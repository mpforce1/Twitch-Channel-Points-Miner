# Twitch Channel Points Miner

<p align="center">
<a href="https://github.com/mpforce1/Twitch-Channel-Points-Miner/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/mpforce1/Twitch-Channel-Points-Miner"></a>
<a href="https://github.com/mpforce1/Twitch-Channel-Points-Miner/stargazers"><img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/mpforce1/Twitch-Channel-Points-Miner"></a>
<a href="https://hits.sh/github.com/mpforce1/Twitch-Channel-Points-Miner/"><img alt="GitHub Traffic" src="https://hits.sh/github.com/mpforce1/hits.svg?style=flat&label=views"/></a>
<a href="https://github.com/mpforce1/Twitch-Channel-Points-Miner/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/mpforce1/Twitch-Channel-Points-Miner?style=flat&color=black&logo=unlicense&logoColor=white"></a>
<a href="https://github.com/mpforce1/Twitch-Channel-Points-Miner"><img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/mpforce1/Twitch-Channel-Points-Miner?style=flat&color=lightyellow&logo=github&logoColor=white"></a>
<a href="https://github.com/mpforce1/Twitch-Channel-Points-Miner/actions/workflows/test.yml"><img alt="Test Status" src="https://img.shields.io/github/actions/workflow/status/mpforce1/Twitch-Channel-Points-Miner/test.yml?branch=main&label=Tests"></a>
</p>


A simple script that will watch a stream for you and earn the channel points.

It can wait for a streamer to go live (+_450 points_ when the stream starts), it will automatically click the bonus
button (_+50 points_), and it will follow raids (_+250 points_).

Read more about the channel points [here](https://help.twitch.tv/s/article/channel-points-guide).

Please read the [getting started](docs/guides/getting-started.md) guide to get set up quickly. For more advanced usage
please read the [advanced usage](docs/guides/advanced-usage.md) guide.

## Contents

<!-- TOC -->
* [Credits](#credits)
* [Community](#community)
* [Core Features](#core-features)
* [Limits](#limits)
* [Common Issues](#common-issues)
* [Disclaimer](#disclaimer)
<!-- TOC -->

## Credits

- [Original idea](https://github.com/gottagofaster236/Twitch-Channel-Points-Miner)
- [Original repository](https://github.com/Tkd-Alex/Twitch-Channel-Points-Miner-v2)
- [Forked from](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2)

## Community

If you want to help with this project, please leave a star 🌟 and share it with your friends! 😎

If you have any issues, or you want to contribute, you are welcome! But please read
the [CONTRIBUTING.md](docs/CONTRIBUTING.md) file.

## Core Features

> [!NOTE]
> The following points are only the base amount you can get. If you are subscribed you will see a proportionally larger
> number depending on your subscription tier.

- Mines channel points for up to 2 channels at a time
- Earns progress for basic rewards (_+10_)
- Claims bonus rewards (_+50_)
- Follows raids (_+250_)
- Earns progress for watch streak rewards (_+300_, _+350_, _+400_, or _+450_ depending on the streak
  count)
- Advances progress for drops
- Claims any earned drops
- Makes predictions using your channel points
- Contributes to community goals using your channel points
- Claims moments
- Joins live channel IRC
- Sends events to fully customisable endpoints (Discord, Telegram, Matrix, Custom, etc...), including events for:
    - Channel points gains/losses
    - Stream up/down
    - Prediction start/end/result
    - Moments
    - Raids
    - User mentions in chat
- Analytics site showing charts with information about the miner's performance
- Fully configurable and extensible (see the [example](example.py))

## Limits

_**Twitch does not allow you to earn channel points on more than 2 channels at the same time. We watch the first two
streamers that have the highest priority according to your configuration.**_

_**Twitch does not all you to earn progress towards more than 1 drops campaign at the same time. When using the `DROPS`
priority, only a single streamer will be selected.**_

## Common Issues

Issues running on Windows. It is not recommended to run the miner on Windows, although you are welcome to try ☺️. Please
run either in a Docker container (recommended) or directly on a Linux system (less
secure). You can get a Linux environment in Windows by installing [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

`run.py` MUST be mounted as a volume (`-v`) when using Docker.

If you don't mount the volume(s) for the analytics (or cookies or logs) folder, data will not be persisted between
docker/miner restarts.

If you don't have a cookie file, or it's your first time running the script, you will need to log in to Twitch. The
miner startup logs will prompt you with a URL you can use to log in.

If you need to run multiple containers you will need to bind different ports per container (only if you need also use
the analytics) and mount different run.py file.

## Disclaimer

This project comes with no guarantee or warranty. You are responsible for whatever happens from using this project. It
is possible to get soft or hard banned by using this project if you are not careful. This is a personal project and is
in no way affiliated with Twitch.
