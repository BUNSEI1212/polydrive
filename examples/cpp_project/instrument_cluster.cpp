#include "cluster_display.h"

// Instrument cluster display for JDM market

void showMaintenanceReminder(int days_left) {
    if (days_left <= 0) {
        display.setText("点検時期が過ぎています");
    } else if (days_left <= 7) {
        display.setText("まもなく点検時期です");
    }
}

void showDoorWarning(DoorStatus door) {
    switch (door) {
        case DOOR_OPEN:
            display.setText("ドアが開いています");
            break;
        case DOOR_AJAR:
            display.setText("ドアが完全に閉じていません");
            break;
    }
}
