#include <hardware/watchdog.h>

// Trivial program meant to run from RAM that just reboots the RP2040.

int main() {
  watchdog_reboot(0, 0, 100);
  return 0;
}
