#include "hmi_display.h"

// Dashboard warning display module

void showBrakeWarning(BrakeStatus status) {
    switch (status) {
        case BRAKE_LOW:
            // TODO: These should be externalized to i18n resources
            display.setText("制动液位过低，请及时补充");
            display.setIcon("warning_brake");
            break;
        case BRAKE_FAULT:
            display.setText("制动系统故障，请立即停车检查");
            display.setIcon("error_brake");
            break;
        case BRAKE_OVERHEAT:
            display.setText("制动器温度过高，请注意冷却");
            display.setIcon("warning_temp");
            break;
    }
}

void showBatteryStatus(int soc_percent) {
    if (soc_percent < 10) {
        display.setText("电量严重不足，请立即充电");
    } else if (soc_percent < 20) {
        display.setText("电量较低，建议尽快充电");
    }
    // "Battery OK" is externalized properly
    char buf[64];
    snprintf(buf, sizeof(buf), "%d%%", soc_percent);
    display.setBatteryLevel(buf);
}
