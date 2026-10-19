# Desktop speaker popping (Logitech Z323)

Investigated 2026-10-19 on dylan-MS-7C84 (Ubuntu). Nothing was changed in software.

## Hardware
- Speakers: Logitech Z323 (2.1, 3.5 mm aux and RCA inputs on the back).
- Board: MSI MAG X570 Tomahawk WiFi (MS-7C84), Realtek ALCS1200A codec.
- Outputs seen (`aplay -l`, `wpctl status`, `/proc/asound/card2/codec#0`):
  - Analog 3.5 mm: rear Line Out front jack active (the one in use); front headphone jack present, muted.
  - Optical S/PDIF out on the rear panel; ALSA exposes it as "ALCS1200A Digital" (card 2, device 1), unused.
  - HDMI audio via the NVIDIA GA104 (4 monitors: VX2452, MP59G, BenQ GL2460, 27N1A).
  - USB: only the Jabra SPEAK 410 (card 3). No USB DAC.
- Mixer on card 2 is not unusual: Master 56, Front/Surround/Center/LFE all 87, PipeWire analog sink at 0.40.

## Symptom
Loud popping, worse with speaker volume, like touching the aux plug. Unplugging the aux at the PC end
stopped it, so the loud part is noise on the PC analog path (ground loop, interference or a worn
cable/jack). A very faint periodic double "duh-duh" pop remains with the PC cable out. It seems
independent of volume and so probably comes from the speakers themselves (power supply or amp).

## Current state (2026-10-19)
Dylan wired the subwoofer's RCA input to a 3.5 mm plug into the computer. Result not yet known.
(Still the onboard analog output, so this only tests the speaker-side input and cable.)

## Next options, cheapest first
1. Compare cables/jacks: another aux cable, front vs rear jack, the cable on a phone.
2. Faint pop: unplug the cable at the speaker end too; try another outlet or power strip; turn the
   volume knob to zero and see if it persists; move the sub away from other electronics.
3. USB sound card or DAC with RCA out (about 10-30 EUR). Preferred: it bypasses the motherboard analog path.
4. Optical to RCA converter (about 10-15 EUR) from the board's optical out. Needs its own power; select the
   "Digital" sink in PipeWire.
5. Ground-loop isolator on the aux cable (about 8 EUR).
6. Optional software check: codec power-save toggling (`snd_hda_intel power_save`) can add pops at idle.
