# Twitch endpoints
URL = "https://www.twitch.tv"               # Browser, Apps
# URL = "https://m.twitch.tv"               # Mobile Browser
# URL = "https://android.tv.twitch.tv"      # TV
IRC = "irc.chat.twitch.tv"
IRC_PORT = 6667
WEBSOCKET = "wss://pubsub-edge.twitch.tv/v1"
HERMES_WEBSOCKET = "wss://hermes.twitch.tv/v1"
CLIENT_ID = "ue6666qo983tsx6so1t0vnawi233wa"        # TV
CLIENT_ID_WEB = "kimne78kx3ncx6brgo4mv6wki5h1ko"    # Browser
# CLIENT_ID = "r8s4dac0uhzifbpu9sjdiwzctle17ff"     # Mobile Browser
# CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"     # Android App
# CLIENT_ID = "851cqzxpb9bqu9z6galo155du"           # iOS App
DROP_ID = "c2542d6d-cd10-4532-919b-3d19f30a768b"
# CLIENT_VERSION = "32d439b2-bd5b-4e35-b82a-fae10b04da70"  # Android App
CLIENT_VERSION = "ef928475-9403-42f2-8a34-55784bd08e16"  # Browser

USER_AGENTS = {
    "Windows": {
        'CHROME': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "FIREFOX": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
    },
    "Linux": {
        "CHROME": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
        "FIREFOX": "Mozilla/5.0 (X11; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0",
    },
    "Android": {
        # "App": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G975N Build/N2G48C) tv.twitch.android.app/13.4.1/1304010"
        "App": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G977N Build/LMY48Z) tv.twitch.android.app/14.3.2/1403020",
        "TV": "Mozilla/5.0 (Linux; Android 7.1; Smart Box C1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }
}

BRANCH = "main"
GITHUB_url = (
    "https://raw.githubusercontent.com/mpforce1/Twitch-Channel-Points-Miner/"
    + BRANCH
)


class GQLOperations:
    url = "https://gql.twitch.tv/gql"
    integrity_url = "https://gql.twitch.tv/integrity"
    WithIsStreamLiveQuery = {
        "operationName": "WithIsStreamLiveQuery",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "04e46329a6786ff3a81c01c50bfa5d725902507a0deb83b0edbf7abe7a3716ea",
            }
        },
    }
    PlaybackAccessToken = {
        "operationName": "PlaybackAccessToken",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9",
            }
        },
    }
    VideoPlayerStreamInfoOverlayChannel = {
        "operationName": "VideoPlayerStreamInfoOverlayChannel",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "e785b65ff71ad7b363b34878335f27dd9372869ad0c5740a130b9268bcdbe7e7",
            }
        },
    }
    ClaimCommunityPoints = {
        "operationName": "ClaimCommunityPoints",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "46aaeebe02c99afdf4fc97c7c0cba964124bf6b0af229395f1f6d1feed05b3d0",
            }
        },
    }
    CommunityMomentCallout_Claim = {
        "operationName": "CommunityMomentCallout_Claim",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "e2d67415aead910f7f9ceb45a77b750a1e1d9622c936d832328a0689e054db62",
            }
        },
    }
    DropsPage_ClaimDropRewards = {
        "operationName": "DropsPage_ClaimDropRewards",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "a455deea71bdc9015b78eb49f4acfbce8baa7ccbedd28e549bb025bd0f751930",
            }
        },
    }
    ChannelPointsContext = {
        "operationName": "ChannelPointsContext",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "7fe050e3761eb2cf258d70ee1a21cbd76fa8cf3d7e7b12fc437e7029d446b5e3",
            }
        },
    }
    JoinRaid = {
        "operationName": "JoinRaid",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "c6a332a86d1087fbbb1a8623aa01bd1313d2386e7c63be60fdb2d1901f01a4ae",
            }
        },
    }
    ModViewChannelQuery = {
        "operationName": "ModViewChannelQuery",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "df5d55b6401389afb12d3017c9b2cf1237164220c8ef4ed754eae8188068a807",
            }
        },
    }
    Inventory = {
        "operationName": "Inventory",
        "variables": {"fetchRewardCampaigns": True},
        # "variables": {},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "8337eb8541b314040b0edde0c09c5c7a2783ba1960aa9edfbf3bac16d0fec404",
            }
        },
    }
    MakePrediction = {
        "operationName": "MakePrediction",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "b44682ecc88358817009f20e69d75081b1e58825bb40aa53d5dbadcc17c881d8",
            }
        },
    }
    ViewerDropsDashboard = {
        "operationName": "ViewerDropsDashboard",
        # "variables": {},
        "variables": {"fetchRewardCampaigns": True},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "d9cae7761dafab85908c85e6683cb4201b449e66ac3bb5e894f15ff12aeafaa7",
            }
        },
    }
    DropCampaignDetails = {
        "operationName": "DropCampaignDetails",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "039277bf98f3130929262cc7c6efd9c141ca3749cb6dca442fc8ead9a53f77c1",
            }
        },
    }
    DropsHighlightService_AvailableDrops = {
        "operationName": "DropsHighlightService_AvailableDrops",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "782dad0f032942260171d2d80a654f88bdd0c5a9dddc392e9bc92218a0f42d20",
            }
        },
    }
    GetIDFromLogin = {
        "operationName": "GetIDFromLogin",
        "variables": {"login": None},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca",
            }
        },
    }
    PersonalSections = (
        {
            "operationName": "PersonalSections",
            "variables": {
                "input": {
                    "sectionInputs": ["FOLLOWED_SECTION"],
                    "recommendationContext": {"platform": "web"},
                },
                "channelLogin": None,
                "withChannelUser": False,
                "creatorAnniversariesExperimentEnabled": False,
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9fbdfb00156f754c26bde81eb47436dee146655c92682328457037da1a48ed39",
                }
            },
        },
    )
    ChannelFollows = {
        "operationName": "ChannelFollows",
        "variables": {"limit": 100, "order": "ASC"},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "eecf815273d3d949e5cf0085cc5084cd8a1b5b7b6f7990cf43cb0beadf546907",
            }
        },
    }
    UserPointsContribution = {
        "operationName": "UserPointsContribution",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "23ff2c2d60708379131178742327ead913b93b1bd6f665517a6d9085b73f661f"
            }
        }
    }
    ContributeCommunityPointsCommunityGoal = {
        "operationName": "ContributeCommunityPointsCommunityGoal",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "5774f0ea5d89587d73021a2e03c3c44777d903840c608754a1be519f51e37bb6"
            }
        }
    }
    RewardList = {
        "operationName": "RewardList",
        "variables": {
            "shouldIncludeAllSuspendedStreaks": False,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "0b1471876d7647993731b9e3c6a13bf304c67fb31d07f06a945d42286ee377c4"
            }
        }
    }
    ChatRoomBanStatus = {
        "operationName": "ChatRoomBanStatus",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "319f2a9a3ac7ddecd7925944416c14b818b65676ab69da604460b68938d22bea"
            }
        }
    }
    SubscriptionsManagement_SubscriptionBenefits = {
        "operationName": "SubscriptionsManagement_SubscriptionBenefits",
        "variables": {"cursor": "", "filter": "GIFT", "limit": 100, "platform": "WEB"},
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "dfac9fc0965996a636f07fd98ae5f9878a628134b330b47a0d26c02a0c225854",
                "version": 1,
            }
        },
    }
    WeeklyVisitRewardsQuery = {
        "operationName": "WeeklyVisitRewardsQuery",
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "ce98e9db55db7e4abcc1f5ac65c933b73c58fa9c4c8afe3c5098a8ed79737a3c",
                "version": 1,
            }
        },
    }
    FilterableVideoTower_Videos = {
        "operationName": "FilterableVideoTower_Videos",
        "variables": {
            "broadcastType": "ARCHIVE",
            "includePreviewBlur": False,
            "limit": 7,
            "videoSort": "TIME",
        },
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "67004f7881e65c297936f32c75246470629557a393788fb5a69d6d9a25a8fd5f",
                "version": 1,
            }
        },
    }
    ClipsCards__User = {
        "operationName": "ClipsCards__User",
        "variables": {
            "criteria": {"filter": "ALL_TIME"},
            "limit": 20,
            # "login": "[username]",
        },
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "1cd671bfa12cec480499c087319f26d21925e9695d1f80225aae6a4354f23088",
                "version": 1,
            }
        },
    }