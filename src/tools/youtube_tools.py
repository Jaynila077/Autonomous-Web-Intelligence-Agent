import os
from googleapiclient.discovery import build
from langchain_core.tools import tool
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

@tool
def search_youtube_videos(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches YouTube for videos matching a specific topic, query, or keyword.
    
    Use this tool to find relevant video content, news reports, or tutorials. 
    This tool ONLY returns metadata (Title, Description, and Video ID). It does 
    NOT return the actual spoken text of the video.
    
    Args:
        query (str): The search term or topic (e.g., 'SpaceX Starship launch').
        max_results (int, optional): The maximum number of videos to retrieve. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the videos. Each dictionary contains:
            - video_id (str): The unique 11-character YouTube Video ID (required for transcript extraction).
            - title (str): The title of the video.
            - description (str): The creator's description of the video.
            - channel (str): The name of the channel that uploaded the video.
            - url (str): The direct link to watch the video.
            
        If the API key is missing or quota is exhausted, returns a list containing a single dictionary with an 'error' key.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return [{"error": "YOUTUBE_API_KEY environment variable is missing. Cannot perform search."}]
        
    extracted_videos = []
    
    try:
        # Build the YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Execute the search request
        request = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=max_results
        )
        response = request.execute()
        
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            extracted_videos.append({
                "video_id": video_id,
                "title": snippet.get('title', 'No Title'),
                "description": snippet.get('description', 'No Description'),
                "channel": snippet.get('channelTitle', 'Unknown Channel'),
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })
            
        return extracted_videos

    except Exception as e:
        return [{"error": f"YouTube Data API error: {str(e)}"}]
