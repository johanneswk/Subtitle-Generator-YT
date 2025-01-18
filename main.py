from googleapiclient.discovery import build
import requests
import datetime
import os

# ==============================
# INSTELLINGEN
# ==============================
# YouTube API-sleutel en kanaal-ID
API_KEY = "JOUW_YOUTUBE_API_SLEUTEL"
CHANNEL_ID = "JOUW_YOUTUBE_CHANNEL_ID"

# Azure Translator API
AZURE_TRANSLATOR_KEY = "JOUW_AZURE_TRANSLATOR_SLEUTEL"
AZURE_TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"
AZURE_TRANSLATOR_REGION = "westeurope"

# Talen om de ondertitels naar te vertalen
TARGET_LANGUAGES = ["en", "de", "fr"]  # Engels, Duits, Frans

# Onderdeel van de YouTube API
youtube = build('youtube', 'v3', developerKey=API_KEY)

# ==============================
# FUNCTIES
# ==============================

def get_videos_from_last_week(channel_id):
    """
    Haal video's op die in de afgelopen 7 dagen zijn gepubliceerd.
    """
    one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    one_week_ago_iso = one_week_ago.isoformat("T") + "Z"  # ISO 8601-formaat

    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        type="video",
        order="date",
        publishedAfter=one_week_ago_iso,
        maxResults=10  # Maximaal aantal video's ophalen
    )
    response = request.execute()

    video_ids = []
    for item in response.get('items', []):
        video_ids.append(item['id']['videoId'])

    return video_ids

def download_subtitles(video_id, language_code="nl"):
    """
    Download de Nederlandse ondertitels van een video.
    """
    request = youtube.captions().list(part="snippet", videoId=video_id)
    response = request.execute()

    for item in response.get('items', []):
        if item['snippet']['language'] == language_code:
            caption_id = item['id']
            download_request = youtube.captions().download(id=caption_id, tfmt="srt")
            subtitle_file = f"dutch_subtitles_{video_id}.srt"
            with open(subtitle_file, "wb") as file:
                file.write(download_request.body)
            print(f"Ondertitels gedownload voor video {video_id}!")
            return subtitle_file

    print(f"Geen Nederlandse ondertitels gevonden voor video {video_id}.")
    return None

def translate_subtitles(input_file, target_languages):
    """
    Vertaal de ondertitels naar meerdere talen.
    """
    translated_files = []
    with open(input_file, "r", encoding="utf-8") as file:
        subtitles = file.read()

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
    }

    for lang in target_languages:
        response = requests.post(
            AZURE_TRANSLATOR_ENDPOINT,
            headers=headers,
            params={"api-version": "3.0", "to": lang},
            json=[{"text": subtitles}]
        )
        response.raise_for_status()
        result = response.json()
        translated_text = result[0]['translations'][0]['text']

        output_file = f"translated_{lang}_{os.path.basename(input_file)}"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(translated_text)
        translated_files.append(output_file)

    print(f"Vertalingen voltooid voor bestand {input_file}!")
    return translated_files

def upload_subtitles(video_id, subtitle_file, language_code):
    """
    Upload de vertaalde ondertitels naar de YouTube-video.
    """
    request = youtube.captions().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "language": language_code,
                "name": f"Ondertitels ({language_code})",
                "isDraft": False
            }
        },
        media_body=subtitle_file
    )
    response = request.execute()
    print(f"Ondertitels geüpload in {language_code} voor video {video_id}!")

# ==============================
# WORKFLOW
# ==============================

def main():
    # Stap 1: Haal video's op van de afgelopen week
    video_ids = get_videos_from_last_week(CHANNEL_ID)
    if not video_ids:
        print("Geen video's gevonden die in de afgelopen week zijn gepubliceerd.")
        return

    # Stap 2: Verwerk elke video
    for video_id in video_ids:
        # Download de Nederlandse ondertitels
        subtitle_file = download_subtitles(video_id, language_code="nl")
        if not subtitle_file:
            continue

        # Vertaal de ondertitels
        translated_files = translate_subtitles(subtitle_file, TARGET_LANGUAGES)

        # Upload de vertaalde ondertitels naar de YouTube-video
        for translated_file, lang in zip(translated_files, TARGET_LANGUAGES):
            upload_subtitles(video_id, translated_file, lang)

if __name__ == "__main__":
    main()
