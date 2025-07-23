
### Generate AI Avatar Photo
```
curl --location 'https://api.heygen.com/v2/photo_avatar/photo/generate' \
--header 'accept: application/json' \
--header 'Content-Type: application/json' \
--header 'X-Api-Key: <your-api-key>' \
--data '{
    "name": "Lina",
    "age": "Young Adult",
    "gender": "Woman",
    "ethnicity": "Asian American",
    "orientation": "horizontal",
    "pose": "half_body",
    "style": "Realistic",
    "appearance": "A stylish East Asian Woman in casual attire walking through a bustling city street"
}'
```

- Response 
```  
{
  "error": null,
  "data": {
    "generation_id": "def3076d2c8b4929acf269d8ea6b562e"
  }
}
```


### Check Generation Status   
```
curl --request GET \
     --url https://api.heygen.com/v2/photo_avatar/generation/4ea4fea89c724fcfb49502c4323bac55 \
     --header 'accept: application/json' \
     --header 'x-api-key: <your_api_key>'
```     

- Response - Success
```
{
    "error": null,
    "data": {
        "id": "def3076d2c8b4929acf269d8ea6b562e",
        "status": "success",
        "msg": null,
        "image_url_list": [
            "https://resource2.heygen.ai/image/701c1dfb977d4d62bef3fda755e2d4c5/original",
            "https://resource2.heygen.ai/image/605e0f207d7b4c2c92923dda0d480583/original",
            "https://resource2.heygen.ai/image/97c92a578a824a2083947285f8b80e4e/original",
            "https://resource2.heygen.ai/image/2632443cb8394276b8d3046ea6748f47/original"
        ],
        "image_key_list": [
            "image/701c1dfb977d4d62bef3fda755e2d4c5/original",
            "image/605e0f207d7b4c2c92923dda0d480583/original",
            "image/97c92a578a824a2083947285f8b80e4e/original",
            "image/2632443cb8394276b8d3046ea6748f47/original"
        ]
    }
}
```