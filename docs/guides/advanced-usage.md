# Advanced Usage

This document is an addition to the [getting started](getting-started.md) guide describing all other ways to get,
configure, and run the miner.

## Getting The Miner

There are several ways you can get the miner, the preferred method is
via [Docker Hub](getting-started.md#getting-the-miner), however you may also use one of the following methods.

### GitHub Releases

> [!IMPORTANT]
> There are currently no releases in the GitHub repository, once one becomes available you can use this method.

In order to download the latest release image and load it into your local docker image store, run the following
commands:

```sh
wget https://github.com/mpforce1/Twitch-Channel-Points-Miner/releases/download/{latest version number}/twitch-channel-points-miner-{platform tag}.tar.gz
docker image load -i [downloaded filename]
```

1. The first command downloads the latest miner release from the GitHub repository releases page.
   `{latest version number}` should be replaced with the current latest version number (e.g. `2.0.0`), and
   `{platform tag}` should be the tag for your platform (e.g. `linux-amd64`). This can be skipped if you've downloaded
   the release manually, just ensure your current working directory contains the downloaded file.
2. The second command loads the downloaded image file into your local docker image store. You should replace
   `[downloaded filename]` with the actual filename of the downloaded file. This step cannot be skipped.

Once this is completed you'll have an image in your local docker image store tagged
`mpforce1/twitch-channel-points-miner:latest`.

### Clone The Repository

> [!WARNING]
> Due to security considerations, it is advised that you don't run the miner directly on your local filesystem. This
> example is included for completeness, please use Docker instead.
 
To clone the repository run the following command:

```sh
git clone git@github.com:mpforce1/Twitch-Channel-Points-Miner.git
```

This command clones this repository into your local filesystem, it'll be in the current working directory in a
directory called 'Twitch-Channel-Points-Miner'.

### Build Locally

In order to build the image locally yourself using the Dockerfile, first [clone](#clone-the-repository) the repository
and then run the following command from within the repository directory:

```sh
docker build --tag mpforce1/twitch-channel-points-miner:latest .
```

This command builds the docker image, tags it as `mpforce1/twitch-channel-points-miner:latest`, and writes the image to
your local docker image store.

## Configuration

Basic configuration is described in the [getting started](getting-started.md) guide. There are too many configuration
options to include in this document so please see [here](advanced-configuration.md) for the full list.

## Running The miner

In order to run the miner you'll need have first written a [configuration](#configuration) file. Once that's done, you
can run using any of the following methods (in addition to the method
described [here](getting-started.md#running-the-miner)):

### Docker Run

This method is suitable if you're just using the Docker Hub image, or you've built an image locally.

```sh
docker run \
    -v $(pwd)/analytics:/usr/src/app/analytics \
    -v $(pwd)/cookies:/usr/src/app/cookies \
    -v $(pwd)/logs:/usr/src/app/logs \
    -v $(pwd)/run.py:/usr/src/app/run.py:ro \
    -p 5000:5000 \
    mpforce1/twitch-channel-points-miner:latest
```

Whichever way you run the miner, the volumes should point to the actual directory or file you want to mount. In the
compose case, we're mounting using relative URIs in the current working directory (`./analytics`, `./cookies`, `./logs`,
and `./run.py`). In the run case, we're doing the same using the `${pwd}` command, which substitues the current working
directory for itself when ran.

The following file needs to be mounted:

- `run.py` : this is your starter script with your configuration

And the following directories can be optionally mounted :

- `analytics` : to save the analytics data
- `cookies` : to provide login information
- `logs` : to keep logs outside of container

Mounting the directories is technically optional, however, in that case no data will be persisted between container
restarts.

Mounting the `run.py` file is not optional as the miner requires one to start.

### Run Locally

> [!WARNING]
> As mentioned previously, it is highly recommended to use Docker instead due to security considerations.

If you want to run the miner locally you must have first [cloned](#clone-the-repository),
and [configured](#configuration) your `run.py` file. You also need to
install [uv](https://docs.astral.sh/uv/getting-started/installation/). Once this is done, you can simply run the
following commands from within the same directory:

```sh
uv sync
uv run run.py
```

1. The first command asks `uv` to get all the project dependencies and install them in your local python environment, by
   default they will be placed in a virtual environment in the local `.venv` directory.
2. The second command runs the miner!

You should then see console output showing the miner startup up.
