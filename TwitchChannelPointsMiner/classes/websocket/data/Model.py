from TwitchChannelPointsMiner.classes.websocket.data import (
    CommunityMomentsChannel,
    CommunityPointsChannel,
    CommunityPointsUser,
    OnsiteNotification,
    PredictionsChannel,
    PredictionsUser,
    Raid,
    UserSubscribeEvents,
    VideoPlaybackById,
    ViewerMilestones,
    WeeklyRewards,
)

Model = (
    CommunityMomentsChannel.Model
    | CommunityPointsChannel.Model
    | CommunityPointsUser.Model
    | OnsiteNotification.Model
    | PredictionsChannel.Model
    | PredictionsUser.Model
    | Raid.Model
    | UserSubscribeEvents.Model
    | VideoPlaybackById.Model
    | ViewerMilestones.Model
    | WeeklyRewards.Model
)
