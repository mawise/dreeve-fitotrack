# dreeve-fitotrack
API wrapper to upload from GPS fitness recording app [FitoTrack](https://codeberg.org/jannis/FitoTrack) to self-hosted tracking app [Dreeve](https://github.com/dreeveapp/dreeve)

## Usage
1. Checkout the repo
2. Configure the docker-compose.yml (or environment variable) with your `DREEVE_UPLOAD_URL`
3. Configure FitoTrack with the correct upload URL: `https://dreeve.example.com/fitotrack-upload?access_token=drv_YOUR_API_KEY`
4. Add an extra redirect in Caddy (or reverse proxy of choice):

```
dreeve.example.com {
    handle /fitotrack-upload {
        # Use 127.0.0.1:8081 if Caddy runs on host, or fitotrack-relay:8081 if Caddy shares the Docker network
        reverse_proxy 127.0.0.1:8081 ## to match the relay
    }

    handle {
        reverse_proxy 127.0.0.1:8080 ## to match your Dreeve installation
    }
}
```
