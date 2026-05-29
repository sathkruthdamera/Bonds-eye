# Bonds-eye stick avatar scope

Bonds-eye MVP uses a rough stick avatar instead of true DensePose.

## Output states

UNKNOWN
NO_PERSON
STANDING_STILL
MOVING
CROUCH_LIKE
LEFT_ZONE
RIGHT_ZONE
CENTER_ZONE

## Live feed fields

presence
confidence
motion_intensity
signal_disturbance
pose_state
stick_avatar

## Notes

The stick avatar is a visual approximation based on RSSI and CSI signal changes. It is not a camera pose and it is not exact body tracking.
