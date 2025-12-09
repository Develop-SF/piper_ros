#!/bin/bash
# interface name -> bitrate
declare -A CAN_TARGETS
CAN_TARGETS["piper_leader"]="1000000"
CAN_TARGETS["piper_follower"]="1000000"

# Whether to ignore CAN quantity check (default false)
IGNORE_CHECK=false

# Parsing parameters
for arg in "$@"; do
    if [ "$arg" == "--ignore" ]; then
        IGNORE_CHECK=true
    fi
done

# Step 1: show CAN_TARGETS configuration
echo "🔧 Checking CAN_TARGETS configuration:"
LINE_NUM=0
for name in "${!CAN_TARGETS[@]}"; do
    LINE_NUM=$((LINE_NUM + 1))
    bitrate="${CAN_TARGETS[$name]}"
    echo "  [$LINE_NUM] \"$name\"=\"$bitrate\""
done

PREDEFINED_COUNT=${#CAN_TARGETS[@]}
CURRENT_CAN_COUNT=$(ip link show type can | grep -c "link/can")

if [ "$IGNORE_CHECK" = false ] && [ "$CURRENT_CAN_COUNT" -ne "$PREDEFINED_COUNT" ]; then
    echo "[WARN]: The detected number of CAN modules ($CURRENT_CAN_COUNT) does not match the expected number ($PREDEFINED_COUNT)."
    read -p "Do you want to continue? (y/N): " user_input
    case "$user_input" in
        [yY]|[yY][eE][sS])
            echo "Continue execution..."
            ;;
        *)
            echo "Exited."
            exit 1
            ;;
    esac
else
    echo "CAN quantity check ignored or matched, continuing..."
fi

SUCCESS_COUNT=0  # Number of CAN interfaces successfully processed
FAILED_COUNT=0   # Expected number of interfaces that failed or were not processed

# Copy a list of CAN_TARGETS keys and mark each one for success
declare -A CAN_STATUS
for name in "${!CAN_TARGETS[@]}"; do
    CAN_STATUS["$name"]="pending"
done

# Handle multiple CAN modules
SYS_INTERFACE=$(ip -br link show type can | awk '{print $1}')

echo -e "\n🔍 [INFO]: The following CAN interfaces were detected in the system:"
for iface in $SYS_INTERFACE; do
    echo "  - $iface"
done

echo -e "\n⚠️  [HINT]: Please make sure the above interface names cover your CAN_TARGETS config."

# Iterate through each CAN interface in CAN_TARGETS
for iface in "${!CAN_TARGETS[@]}"; do
    echo "--------------------------- $iface ------------------------------"

    if ! ip link show "$iface" &>/dev/null; then
        echo "[ERROR]: Interface '$iface' was not found in the system."
        echo "[HINT]: Please check if the USB-CAN device for '$iface' is plugged in and udev rules are working."
        echo "-----------------------------------------------------------------"
        continue
    fi

    TARGET_NAME="$iface"
    TARGET_BITRATE="${CAN_TARGETS[$iface]}"

    # Check if the current interface is activated
    IS_LINK_UP=$(ip link show "$iface" | grep -q "UP" && echo "yes" || echo "no")

    # Get the bit rate of the current interface
    CURRENT_BITRATE=$(ip -details link show "$iface" | grep -oP 'bitrate \K\d+')

    if [ "$IS_LINK_UP" = "yes" ] && [ -n "$CURRENT_BITRATE" ] && [ "$CURRENT_BITRATE" -eq "$TARGET_BITRATE" ]; then
        echo "[INFO]: Interface '$iface' is activated and bitrate is $TARGET_BITRATE"
    else
        if [ "$IS_LINK_UP" = "yes" ]; then
            echo "[INFO]: Interface '$iface' is activated, but the bitrate ${CURRENT_BITRATE:-unknown} does not match the set $TARGET_BITRATE."
        else
            echo "[INFO]: Interface '$iface' is not activated or the bitrate is not set."
        fi

        # Set the interface bit rate and activate it
        sudo ip link set "$iface" down
        sudo ip link set "$iface" type can bitrate "$TARGET_BITRATE"
        sudo ip link set "$iface" up
        echo "[INFO]: Interface '$iface' has been reset to bitrate $TARGET_BITRATE and activated."
    fi

    CAN_STATUS["$iface"]="success"
    SUCCESS_COUNT=$((SUCCESS_COUNT+1))
    echo "-----------------------------------------------------------------"
done

# Calculation failed iface
for name in "${!CAN_STATUS[@]}"; do
    if [ "${CAN_STATUS[$name]}" != "success" ]; then
        echo "❌ Expected CAN interface '$name' was not found or not activated."
        FAILED_COUNT=$((FAILED_COUNT+1))
    fi
done

# Final Tips
if [ "$SUCCESS_COUNT" -gt 0 ]; then
    echo "[RESULT]: ✅ $SUCCESS_COUNT expected CAN interfaces processed successfully."
else
    echo "[RESULT]: ❌ No CAN interface matches the preset CAN_TARGETS configuration, please check whether devices are connected correctly and udev rules are in effect."
fi

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "[RESULT]: 🚫 $FAILED_COUNT expected CAN interfaces failed to activate or were not found."
fi
