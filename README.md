# 🧙‍♂️ BilBot Baggins

*"In a server in the cloud, there lived a bot..."*

Convert your TXT and PDF files into high-quality MP3 audiobooks using AI voices. Named after the most famous hobbit who went on unexpected journeys, BilBot helps your documents embark on their own adventure—from static text to spoken word.

## ✨ Features

### 📖 **Smart Text Processing**
- **Multi-format support**: PDF and TXT files
- **Intelligent OCR**: Automatically applies OCR when needed for better text quality
- **Advanced cleaning**: Removes headers, footnotes, references, and formatting artifacts
- **Smart sentence splitting**: Respects abbreviations and handles complex punctuation
- **Spacing correction**: Fixes common PDF extraction issues like "w as" → "was"

### 🎧 **Professional Audio Generation**
- **Neural AI voices**: Multiple high-quality English voices
- **Voice customization**: Adjust rate, and pitch
- **Smart chunking**: Optimizes text segments for natural speech flow
- **Sentence-aware splitting**: Never breaks sentences mid-word
- **Batch processing**: Efficiently handles long documents

### 🏠 **Hobbit-Friendly Interface**
- **Streamlit web app**: Clean, intuitive interface
- **Real-time progress**: See your audiobook being crafted
- **Dual downloads**: Get both the MP3 and cleaned text
- **Session memory**: Maintains state during processing
- **Error handling**: Graceful recovery from processing issues

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- `ocrmypdf` (for PDF OCR processing)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd bilbot-baggins

# Install Python dependencies
pip install -r requirements.txt

# Install ocrmypdf (Ubuntu/Debian)
sudo apt-get install ocrmypdf

# Or on macOS with Homebrew
brew install ocrmypdf
Run the Application
bashstreamlit run app.py
Open your browser to http://localhost:8501 and start converting!
📚 How It Works
```

### Run the Application
```bash
streamlit run app.py
```
Open your browser to http://localhost:8501 and start converting!

📚 How It Works
1. Upload: Drop your PDF or TXT file into the interface
2. Configure: Choose your voice and cleaning options
3. Process: BilBot extracts, cleans, and chunks your text
4. Generate: AI voices bring your text to life
5. Download: Get your MP3 audiobook and cleaned text

### Technical Details
Text Processing Pipeline

Raw File → Text Extraction → OCR (if needed) → Cleaning → Chunking → TTS → MP3

### Key Components
* extractors.py: Multi-library PDF extraction with quality scoring
* cleaners.py: Comprehensive text cleaning and normalization
* chunking.py: Smart sentence-aware text segmentation
* processor.py: Orchestrates the entire text processing pipeline

### PDF Processing Strategy
1. Attempts extraction with multiple libraries (pdfplumber, PyMuPDF, pypdf)
2. Scores text quality using metrics like word length and spacing
3. Applies OCR when native extraction quality is poor
4. Compares OCR vs native results and chooses the best

### Text Cleaning Features
* Fixes hyphenated line breaks
* Removes running headers and page numbers
* Strips footnote markers and references
* Normalizes quotes and special characters
* Corrects punctuation spacing
* Handles "jammed" text (missing spaces)

### Configuration Options
Voice Settings
* Voice: Choose from 20+ English neural voices
* Rate: Adjust speaking speed (-50% to +50%)
* Pitch: Modify voice pitch (-300Hz to +300Hz)

Text Cleaning
* Remove Headers: Strip running headers and page numbers
* Remove Footnotes: Clean footnote markers and references

### File Support
Supported Formats
* PDF: Any PDF with text or images (OCR applied automatically)
* TXT: Plain text files in UTF-8 or Latin-1 encoding

File Size Limits
* Designed for documents up to ~500 pages
* Automatic chunking prevents memory issues
* Processing time scales with document length

### Known Limitations
* OCR Complexity: Image-based PDFs may have text recognition errors
* Language Support: Optimized for English text only
* Complex Layouts: Tables and multi-column layouts may not convert perfectly
* Special Characters: Some Unicode characters may be simplified

### Development

Project Structure

bilbot-baggins/
├── app.py                 # Main Streamlit application
├── text_processor.py      # Main processing interface
├── textproc/              # Text processing modules
│   ├── processor.py       # Main processor class
│   ├── extractors.py      # PDF text extraction
│   ├── cleaners.py        # Text cleaning functions
│   └── chunking.py        # Smart text chunking
├── assets/                # Images and static files
└── requirements.txt       # Python dependencies

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your improvements
4. Test thoroughly
5. Submit a pull request

### Common Issues
"ERROR: Not a valid PDF file"
* Ensure your file is a proper PDF (not a renamed image)
* Try re-saving the PDF from your PDF viewer

Poor audio quality
* Check the source text quality
* Try adjusting voice settings
* Consider manual text cleanup for complex documents

OCR taking too long
* Large image-based PDFs can take several minutes
* Check your ocrmypdf installation
* Consider processing smaller sections

Missing audio for some text
* Check for special characters that might break TTS
* Review the cleaned text output for issues

### Acknowledgments
* Built with Streamlit for the web interface
* Uses Edge TTS for speech synthesis
* PDF processing powered by pdfplumber, PyMuPDF, and pypdf
* OCR capabilities via ocrmypdf
