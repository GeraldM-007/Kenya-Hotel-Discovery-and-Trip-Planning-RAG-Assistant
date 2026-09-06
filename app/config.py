#site URL
KWS_URL = "https://kws.go.ke/experiences"

#user agent to identify where the request is coming from(not a bot)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

#number of pages to scrape data from
pages = 15

DESTINATIONS = [
    {
        "name": "Diani",
        "slug": "diani",
        "url": "https://magicalkenya.com/place-to-go/diani/",
    },
    {
        "name": "Maasai Mara",
        "slug": "maasai-mara",
        "url": "https://magicalkenya.com/place-to-go/maasai-mara/",
    },
    {
        "name": "Chale Island Reef",
        "slug": "chale-island-reef",
        "url": "https://magicalkenya.com/place-to-go/chale-island-reef/",
    },
    {
        "name": "Nanyuki",
        "slug": "nanyuki",
        "url": "https://magicalkenya.com/place-to-go/nanyuki/",
    },
    {
        "name": "Mount Longonot",
        "slug": "mount-longonot",
        "url": "https://magicalkenya.com/place-to-go/mount-longonot/",
    },
    {
        "name": "Ol Pejeta Conservancy",
        "slug": "ol-pejeta-conservancy",
        "url": "https://magicalkenya.com/place-to-go/ol-pejeta-conservancy/",
    },
    {
        "name": "Turkana",
        "slug": "turkana",
        "url": "https://magicalkenya.com/place-to-go/turkana/",
    },
    {
        "name": "Rift Valley",
        "slug": "Rift-Valley",
        "url": "https://magicalkenya.com/place-to-go/the-great-rift-valley/",
    },
    {
        "name": "Kilifi",
        "slug": "Kilifi-Coast",
        "url": "https://magicalkenya.com/place-to-go/kilifi-coast/",
    },
]
