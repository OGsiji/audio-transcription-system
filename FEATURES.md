# Features Overview

## Smart Skip System

### What It Does
The service automatically detects and skips files that have already been transcribed, saving time and API costs.

### How It Works
1. Before transcribing a file, the service checks if both output files exist:
   - `filename_transcription.json`
   - `filename_transcript.txt`

2. If both files exist:
   - ✅ File is skipped
   - 📂 Existing transcription is loaded
   - 📝 Result is included in the batch
   - ⏭️ Logged with skip emoji

3. If files don't exist or are incomplete:
   - 🎤 File is transcribed normally
   - 💾 Both JSON and TXT are saved

### Benefits
- **Save Time**: No re-processing of completed files
- **Save Money**: Avoid duplicate Gemini API calls
- **Resumable**: Restart interrupted jobs without losing progress
- **Incremental**: Add new files to folder and only process new ones

### Example Scenario

**Folder Contents:**
```
my_sermons/
├── sermon_jan_1.mp3  ✅ Already transcribed
├── sermon_jan_8.mp3  ✅ Already transcribed
├── sermon_jan_15.mp3 🆕 New file
└── sermon_jan_22.mp3 🆕 New file
```

**What Happens:**
```
⏭️  Skipping already transcribed file: sermon_jan_1.mp3
⏭️  Skipping already transcribed file: sermon_jan_8.mp3
Processing file 3/4: sermon_jan_15.mp3
Processing file 4/4: sermon_jan_22.mp3
```

**Result:**
- Only 2 files transcribed (saves ~5 minutes and API calls)
- All 4 files included in combined transcript
- Consistent output directory structure

### Force Re-transcription
To force re-transcription of a file, delete its output files:
```bash
rm transcriptions/job-id/filename_transcription.json
rm transcriptions/job-id/filename_transcript.txt
```

## Timestamp-Free Transcripts

### What Changed
Formatted text transcripts (.txt) no longer include timestamp markers in the main body.

### Before (Old Format)
```
[00:00]
Welcome to the session.

[00:15]
Today we'll discuss prayer.

[00:30]
Let me share three principles.
```

### After (New Format)
```
Welcome to the session. Today we'll discuss prayer and spiritual growth. This
is a topic that affects all believers in their daily walk with God.

Let me share three principles that have helped many maintain consistency in
their prayer life. The first principle is...
```

### Why This Change?
1. **Better Readability**: Text flows naturally like a book
2. **Google Docs Ready**: No cleanup needed before sharing
3. **Professional Appearance**: Looks like a proper document
4. **Easier to Read**: Less visual clutter for long transcripts
5. **Print Friendly**: Better for PDF export or printing

### Timestamps Still Available
If you need timestamps for reference or analysis:
- Use the JSON file (`filename_transcription.json`)
- Contains structured timestamp data: `{"time": "00:00", "text": "..."}`
- Programmatically accessible

### Example Use Cases

#### Use Case 1: Documentation
**Need:** Clean document for archival
**Solution:** Use the .txt file (no timestamps)
```bash
cat transcriptions/job-id/sermon_transcript.txt
```

#### Use Case 2: Video Editing
**Need:** Precise timing for cutting clips
**Solution:** Use the .json file (with timestamps)
```bash
cat transcriptions/job-id/sermon_transcription.json | jq '.timestamps'
```

## Formatted Output Features

### Professional Headers
Every transcript includes:
- Filename
- Date transcribed
- Detected language
- Speaker identification
- Processing time
- Model used

### Optional Sections
If available, transcripts include:
- **Summary**: Brief overview of content
- **Key Topics**: Bullet-pointed main themes

### Text Formatting
- **Line Width**: 80 characters (optimal for reading)
- **Paragraph Breaks**: Every 4-5 sentences
- **UTF-8 Encoding**: Supports all languages
- **Clean Layout**: Consistent spacing and separators

### Combined Transcripts
Automatically created for batch jobs:
- Single file with all transcripts
- Chronological order
- File headers for navigation
- Full searchability

## Output Structure

For every transcription job, you get:

```
transcriptions/
└── job-abc123/
    ├── audio1_transcription.json      # Structured data
    ├── audio1_transcript.txt          # Clean readable text
    ├── audio2_transcription.json
    ├── audio2_transcript.txt
    ├── audio3_transcription.json
    ├── audio3_transcript.txt
    └── combined_transcript.txt        # All files merged
```

### File Purposes

#### JSON Files (`*_transcription.json`)
**Purpose:** Machine-readable data
**Use For:**
- Further processing or analysis
- Programmatic access to timestamps
- Metadata extraction
- API integrations
- Data science workflows

#### Text Files (`*_transcript.txt`)
**Purpose:** Human-readable documents
**Use For:**
- Reading and review
- Copying to Google Docs
- Sharing with team
- Archival documentation
- Printing or PDF export

#### Combined File (`combined_transcript.txt`)
**Purpose:** Single document view
**Use For:**
- Reviewing multiple recordings at once
- Full-text search across all files
- Single document for distribution
- Complete archive of a series

## Integration Examples

### Copy to Google Docs
```bash
# View transcript
cat transcriptions/job-id/sermon_transcript.txt

# Copy and paste into Google Docs
# Format is preserved automatically!
```

### Search Across All Transcripts
```bash
# Find mentions of "prayer" in all transcripts
grep -i "prayer" transcriptions/job-id/combined_transcript.txt
```

### Extract Summaries
```bash
# Get just the summaries from JSON files
for file in transcriptions/job-id/*_transcription.json; do
    jq '.summary' "$file"
done
```

### Count Words
```bash
# Count words in a transcript
wc -w transcriptions/job-id/sermon_transcript.txt
```

## Performance Characteristics

### Smart Skip Performance
- File existence check: < 1ms
- Load existing JSON: < 10ms per file
- Time saved: 30-300 seconds per file (depends on audio length)

### Formatting Performance
- Text formatting: < 100ms per transcript
- No impact on transcription speed
- Generated simultaneously with JSON

### Combined Transcript
- Creation time: < 1 second for 10 files
- Always regenerated (includes all files)
- Negligible overhead

## Configuration

No configuration needed! Both features are:
- ✅ Enabled by default
- ✅ Automatic and transparent
- ✅ Backward compatible
- ✅ Zero maintenance

## Best Practices

### For Smart Skip
1. **Use consistent output directories** for each project
2. **Don't delete output files** unless you want to re-transcribe
3. **Organize by project** to keep related transcripts together

Example:
```bash
# Good: Organized by project
transcriptions/
├── sermons-2025/
├── meetings-q1/
└── podcast-season-1/

# Less ideal: Everything in one folder
transcriptions/
└── random-job-ids/
```

### For Readability
1. **Use .txt files for sharing** - clean and professional
2. **Use .json files for processing** - structured and complete
3. **Use combined transcript for overview** - see everything at once

### For Long-Running Jobs
1. **Monitor with monitor_job.py** - see progress in real-time
2. **Check logs for skip messages** - understand what's being processed
3. **Use same output directory on retry** - leverage Smart Skip

## Troubleshooting

### File Not Skipped When Expected
**Problem:** File is being re-transcribed even though it exists

**Solutions:**
1. Check both files exist (JSON and TXT)
2. Verify you're using the same output directory
3. Check file permissions (must be readable)

### Want to Force Re-transcription
**Problem:** Need to re-transcribe a file that was skipped

**Solution:**
```bash
# Delete both output files
rm transcriptions/job-id/filename_transcription.json
rm transcriptions/job-id/filename_transcript.txt

# Re-run the job
```

### Transcript Format Issues
**Problem:** Text formatting looks wrong

**Solutions:**
1. Check encoding (should be UTF-8)
2. View in a text editor that supports line wrapping
3. Ensure terminal width is at least 80 characters
4. Open in Google Docs for best viewing experience
