import streamlit as st
import os
import tempfile
import asyncio
import time
from typing import List, Dict, Any

import edge_tts
from text_processor import TextProcessor


class AudioConfig:
    """Configuration settings for the audiobook generator"""
    MAX_CHUNK_LENGTH = 2000
    BATCH_SIZE = 5
    SUPPORTED_FORMATS = ["txt", "pdf"]
    DEFAULT_VOICE = "en-US-AndrewNeural"
    TEMP_DIR_PREFIX = "audiobook_"
    MAX_RETRIES = 3
    
    QUALITY_SETTINGS = {
        "Fast (Lower Quality)": {"chunk_size": 3000, "rate_modifier": "+10%"},
        "Balanced": {"chunk_size": 2000, "rate_modifier": "0%"},
        "High Quality (Slower)": {"chunk_size": 1500, "rate_modifier": "-10%"}
    }


class AudioBookGenerator:
    """Main class for generating audiobooks"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        session_vars = {
            'processed_text': None,
            'audio_data': None,
            'download_filename': None,
            'text_stats': None,
            'processing_progress': {},
            'temp_files': [],
            'current_chunks': None
        }
        
        for var, default in session_vars.items():
            if var not in st.session_state:
                st.session_state[var] = default

    @st.cache_data
    def get_available_voices(_self):
        """Get list of US English Male Neural voices"""
        try:
            voices = asyncio.run(edge_tts.list_voices())
            us_male_voices = [
                v for v in voices 
                if (v.get("Locale", "").startswith("en-US") and 
                    "Neural" in v.get("ShortName", "") and
                    v.get("Gender", "").lower() == "male")
            ]
            return sorted(us_male_voices, key=lambda x: x.get("ShortName", ""))
        except Exception as e:
            st.error(f"Error getting voices: {e}")
            return []

    async def generate_speech_with_retry(self, text: str, voice: str, rate: str, pitch: str, output_file: str) -> bool:
        """Generate speech with retry logic"""
        for attempt in range(AudioConfig.MAX_RETRIES):
            try:
                communicate = edge_tts.Communicate(
                    text=text, 
                    voice=voice, 
                    rate=rate, 
                    pitch=pitch
                )
                await communicate.save(output_file)
                return os.path.exists(output_file) and os.path.getsize(output_file) > 0
            except Exception as e:
                if attempt == AudioConfig.MAX_RETRIES - 1:
                    st.error(f"Failed after {AudioConfig.MAX_RETRIES} attempts: {e}")
                    return False
                st.warning(f"Attempt {attempt + 1} failed, retrying in 1 second...")
                await asyncio.sleep(1)
        return False

    def combine_audio_files(self, file_list: List[str]) -> bytes:
        """Combine multiple MP3 files into one"""
        combined_data = b""
        
        for file_path in file_list:
            try:
                with open(file_path, 'rb') as f:
                    mp3_data = f.read()
                    combined_data += mp3_data
            except Exception as e:
                st.error(f"Error reading audio file {file_path}: {e}")
        
        return combined_data

    def show_progress_with_eta(self, current: int, total: int, start_time: float):
        """Show progress with estimated time remaining"""
        progress = current / total if total > 0 else 0
        elapsed = time.time() - start_time
        eta = (elapsed / progress - elapsed) if progress > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Progress", f"{current}/{total}")
        with col2:
            st.metric("Elapsed", f"{elapsed:.1f}s")
        with col3:
            st.metric("ETA", f"{eta:.1f}s" if eta < 3600 else f"{eta/60:.1f}m")

    async def generate_voice_sample(self, voice: str, rate: int, pitch: int) -> bytes:
        """Generate a voice sample for preview"""
        sample_text = "Hello! This is how this voice sounds. Would you like to use this voice for your audiobook?"
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            try:
                success = await self.generate_speech_with_retry(
                    sample_text, voice, f"{rate:+d}%", f"{pitch:+d}Hz", temp_file.name
                )
                if success:
                    with open(temp_file.name, 'rb') as f:
                        audio_data = f.read()
                    return audio_data
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        return b""

    def process_file(self, uploaded_file, clean_text: bool, quality_setting: str) -> bool:
        """Process uploaded file and prepare for audio generation"""
        try:
            # Read file content
            with st.spinner("Reading file..."):
                file_content = uploaded_file.read()
                filename = uploaded_file.name
                
                if filename.lower().endswith(".txt"):
                    text_content = self.text_processor.read_text_file(file_content)
                else:
                    text_content = self.text_processor.read_pdf_file(file_content)
            
            if not text_content.strip():
                st.error("No text found in the file. For PDFs, make sure it contains selectable text, not just images.")
                return False
            
            # Clean text if requested
            if clean_text:
                with st.spinner("Cleaning text..."):
                    text_content = self.text_processor.clean_text(text_content)
            
            # Get chunk size from quality setting
            chunk_size = AudioConfig.QUALITY_SETTINGS[quality_setting]["chunk_size"]
            
            # Split into chunks
            text_chunks = self.text_processor.smart_split_into_chunks(text_content, chunk_size)
            
            if not text_chunks:
                st.error("No text chunks to process. The text might be too short or empty after cleaning.")
                return False
            
            # Store in session state
            st.session_state.processed_text = text_content
            st.session_state.current_chunks = text_chunks
            st.session_state.text_stats = self.text_processor.get_text_stats(text_content)
            
            # Show processing results
            stats = st.session_state.text_stats
            st.success(f"✅ Processed {stats['characters']:,} characters ({stats['words']:,} words) into {len(text_chunks)} audio chunks")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Estimated Reading Time", f"{stats['reading_time_minutes']:.1f} min")
            with col2:
                st.metric("Estimated Audio Length", f"{stats['estimated_audio_minutes']:.1f} min")
            with col3:
                st.metric("Audio Chunks", len(text_chunks))
            
            return True
            
        except Exception as e:
            st.error(f"Error processing file: {e}")
            return False

    async def generate_audiobook(self, voice: str, rate: int, pitch: int) -> bool:
        """Generate audiobook from processed chunks"""
        if not st.session_state.current_chunks:
            st.error("No text chunks available. Please process a file first.")
            return False
        
        text_chunks = st.session_state.current_chunks
        temp_files = []
        temp_dir = tempfile.mkdtemp(prefix=AudioConfig.TEMP_DIR_PREFIX)
        
        try:
            st.info("🎙️ Starting audio generation...")
            progress_bar = st.progress(0)
            status_container = st.container()
            
            start_time = time.time()
            
            # Generate audio for each chunk
            for i, chunk in enumerate(text_chunks):
                if not chunk.strip():
                    continue
                
                with status_container:
                    st.text(f"🎵 Generating audio for chunk {i+1} of {len(text_chunks)}...")
                    self.show_progress_with_eta(i, len(text_chunks), start_time)
                
                temp_file = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
                
                # Generate speech
                success = await self.generate_speech_with_retry(
                    chunk, voice, f"{rate:+d}%", f"{pitch:+d}Hz", temp_file
                )
                
                if success:
                    temp_files.append(temp_file)
                    st.write(f"✅ Chunk {i+1} completed ({len(chunk)} characters)")
                else:
                    st.warning(f"⚠️ Failed to generate chunk {i+1}")
                
                progress_bar.progress((i + 1) / len(text_chunks))
            
            if not temp_files:
                st.error("❌ No audio files were generated successfully.")
                return False
            
            # Combine audio files
            status_container.text("🔗 Combining audio files...")
            final_audio = self.combine_audio_files(temp_files)
            
            if not final_audio:
                st.error("❌ Failed to combine audio files.")
                return False
            
            # Store results
            base_filename = os.path.splitext(uploaded_file.name)[0]
            download_filename = f"{base_filename}_audiobook_{voice}.mp3"
            
            st.session_state.audio_data = final_audio
            st.session_state.download_filename = download_filename
            st.session_state.temp_files = temp_files
            
            # Clear progress indicators
            progress_bar.empty()
            status_container.empty()
            
            # Show audio preview
            if temp_files:
                with st.expander("🔊 Audio Preview (First Chunk)", expanded=False):
                    with open(temp_files[0], 'rb') as f:
                        st.audio(f.read(), format='audio/mp3')
            
            st.success("🎉 Audiobook generated successfully!")
            st.info(f"📊 Generated {len(temp_files)} audio segments totaling {len(final_audio):,} bytes")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error generating audiobook: {str(e)}")
            return False
        
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            try:
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Text to Audiobook Converter", 
        page_icon="🎧", 
        layout="centered"
    )
    
    st.title("🎧 Text to Audiobook Converter")
    st.write("Convert your text files or PDFs into MP3 audiobooks using US English male AI voices!")
    
    # Initialize generator
    generator = AudioBookGenerator()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload a text file or PDF", 
        type=AudioConfig.SUPPORTED_FORMATS,
        help="Choose a .txt file or searchable PDF to convert to audio"
    )
    
    # Voice selection
    voices = generator.get_available_voices()
    if not voices:
        st.error("Could not load voice list. Please refresh the page.")
        st.stop()
    
    voice_options = [v.get("ShortName") for v in voices]
    st.write(f"**Available voices:** {len(voice_options)} US English Male Neural voices")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_voice = st.selectbox(
            "Choose a male voice", 
            voice_options,
            index=voice_options.index(AudioConfig.DEFAULT_VOICE) if AudioConfig.DEFAULT_VOICE in voice_options else 0
        )
    
    with col2:
        if st.button("🎵 Preview Voice"):
            with st.spinner("Generating voice sample..."):
                sample_audio = asyncio.run(generator.generate_voice_sample(selected_voice, 0, 0))
                if sample_audio:
                    st.audio(sample_audio, format='audio/mp3')
    
    # Voice settings
    col1, col2, col3 = st.columns(3)
    with col1:
        speech_rate = st.slider("Speech Rate", -50, 50, 0, help="Negative = slower, Positive = faster")
    with col2:
        speech_pitch = st.slider("Pitch", -20, 20, 0, help="Negative = lower, Positive = higher")
    with col3:
        quality_setting = st.selectbox(
            "Quality Setting", 
            list(AudioConfig.QUALITY_SETTINGS.keys()), 
            index=1,
            help="Higher quality = slower processing but better results"
        )
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        clean_whitespace = st.checkbox("Clean up text formatting", value=True, 
            help="Removes OCR errors, fixes spacing, handles quotes, and cleans up hyphenation issues")
    with col2:
        show_preview = st.checkbox("Show text preview", value=False,
            help="Preview and download the processed text before generating audio")
    
    # Process file button
    if uploaded_file and st.button("📄 Process File", type="secondary"):
        generator.process_file(uploaded_file, clean_whitespace, quality_setting)
    
    # Show text preview and download if available
    if st.session_state.processed_text and show_preview:
        with st.expander("📄 Text Preview & Download", expanded=True):
            st.markdown("**Text Statistics:**")
            if st.session_state.text_stats:
                stats = st.session_state.text_stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Characters", f"{stats['characters']:,}")
                with col2:
                    st.metric("Words", f"{stats['words']:,}")
                with col3:
                    st.metric("Paragraphs", stats['paragraphs'])
            
            st.markdown("**Text Preview (first 500 characters):**")
            preview_text = st.session_state.processed_text[:500] + "..." if len(st.session_state.processed_text) > 500 else st.session_state.processed_text
            st.text_area("Preview", preview_text, height=150, disabled=True)
            
            # Download processed text
            base_filename = os.path.splitext(uploaded_file.name)[0]
            processed_filename = f"{base_filename}_processed.txt"
            
            st.download_button(
                label="📥 Download Processed Text",
                data=st.session_state.processed_text.encode('utf-8'),
                file_name=processed_filename,
                mime="text/plain",
                key="download_text"
            )
    
    # Generate audiobook button
    if st.session_state.current_chunks and st.button("🎵 Generate Audiobook", type="primary"):
        asyncio.run(generator.generate_audiobook(selected_voice, speech_rate, speech_pitch))
    
    # Show audio download if available
    if st.session_state.audio_data:
        st.success("🎉 Audiobook ready for download!")
        
        st.download_button(
            label="📥 Download MP3 Audiobook",
            data=st.session_state.audio_data,
            file_name=st.session_state.download_filename,
            mime="audio/mpeg",
            type="primary",
            key="download_audio"
        )
        
        # Option to clear and start over
        if st.button("🔄 Start Over"):
            # Clear session state
            for key in ['processed_text', 'audio_data', 'download_filename', 'text_stats', 'current_chunks']:
                st.session_state[key] = None
            st.rerun()
    
    # Tips section
    st.markdown("---")
    st.markdown("**Tips:**")
    st.markdown("• Process your file first, then generate the audiobook")
    st.markdown("• Use voice preview to test different voices before generating")
    st.markdown("• Higher quality settings take longer but produce better results")
    st.markdown("• Text cleaning fixes common OCR and formatting issues")
    st.markdown("• Large files may take several minutes to process")
    st.markdown("• If generation fails, check your internet connection and try again")


if __name__ == "__main__":
    main()
