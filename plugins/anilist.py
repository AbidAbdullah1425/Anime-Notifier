# plugins/anilist.py
import requests

ANILIST_API_URL = 'https://graphql.anilist.co'

def fetch_anime_schedule():
    query = '''
    query {
      Page(page: 1, perPage: 50) {
        media(type: ANIME, sort: START_DATE_DESC) {
          id
          title {
            romaji
            english
            native
          }
          airingSchedule {
            nodes {
              episode
              airingAt
            }
          }
          status
        }
      }
    }
    '''
    
    response = requests.post(ANILIST_API_URL, json={'query': query})
    response.raise_for_status()
    
    return response.json()['data']['Page']['media']