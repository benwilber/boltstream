# Boltstream
Self-hosted Live Video Streaming Website + Backend

Reference website: [https://boltstream.me](https://boltstream.me)

## Features

* Live stream via RTMP with a stream key to your RTMP ingest server
* Any number of simultaneous live streams
* Playback via standard HLS
* Restrict playback with HLS segment encryption (AES-128)
	* Pay-per-view
	* Pay-per-minute :-)
* Capture VODs (recordings) of live streams
	* Live-clipping of VODs via nginx-vod-module
* Timed metadata via WebVTT
	* Synchronized chat room messages
	* Synchronized play-by-play live sports events


## Core Components

* [Django](https://www.djangoproject.com/)
	* Web application
* [nginx](https://nginx.org/)
	* Web server
* [nginx-rtmp](https://github.com/arut/nginx-rtmp-module)
	* RTMP ingest
	* Actually, we use a [fork](https://github.com/sergey-dryabzhinsky/nginx-rtmp-module) that adds a number of features that we use.  The original nginx-rtmp hasn't been updated in years.
* [nginx-vod-module](https://github.com/kaltura/nginx-vod-module)
	* HLS VODs
	* Live clipping
* [FFMPEG](https://ffmpeg.org/)
	* Various video encoding/packaging

## Optional Components

* [SportRadar](https://www.sportradar.com/)
	* Realtime sports play-by-play data synchronized to your live streams
* [ACRCloud](https://www.acrcloud.com/)
	* Audio content recognition (Shazaam for your live streams)

	
## Getting Started

Clone this repo!

There is a [Terraform](https://terraform.io/) configuration for deploying this infrastructure on [DigitalOcean](https://www.digitalocean.com/).

First, edit `ansible/site.yml` and update all the variables like `<your ...variable_here>`.

You will also need to modify some variables in `terraform/terraform.tfvars`, and then from within the `terraform` directory, just run:

```bash
$ make apply
```

At the end of the Terraform deployment (might take 10-15 minutes), you will have a full self-hosted live video streaming platform with your own RTMP ingest and playback endpoints.

Happy Streaming!

## Help Wanted!

I put this stack together about a year ago and haven't been able to push much further on it.

Ideally it could be deployed in Docker (I don't know anything about Docker or Kubernetes).  The nginx and Django stuff seems like it could be pretty easy to containerize.

Help me package this up!  We more federated live-streaming platforms!  It just always be Twitch.tv, YouTube, and Facebook!