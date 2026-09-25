# Entrance Observer — Phase 3 device design

Concept design of the production Entrance Observer: a slim camera arch that hangs on a hive entrance. It is a design proposal to review, not a frozen spec. The energy and cost figures are estimates until the Phase 2 units are measured.

[![Entrance Observer on a hive: small opal roof over the head, graphite side arms, landing board with calibration markers](hero.png)](https://gratheon.com/products/entrance_observer/)

- **3D model:** open [`3d-model/index.html`](../3d-model/index.html) (self-contained, works offline) or see [gratheon.com/products/entrance_observer](https://gratheon.com/products/entrance_observer/). [`3d-model/entrance-observer.glb`](../3d-model/entrance-observer.glb) contains the exploded-view animation.
- **Source:** `3d-model/observer-model.js` holds every dimension. The viewer shares its code and scene with the [beehive scale](https://github.com/Gratheon/beehive-sensors/tree/main/model) and [Robotic Beehive](https://github.com/Gratheon/robotic-beehive/tree/main/model) models and uses the same axes, so the three can be placed together.

## What the device is

| | |
| --- | --- |
| **Form** | A slim arch over the landing board: two side arms, a head across the top, a small ridged opal roof over the head, and a hinged landing board between the arms. A 40 mm porch moves the doorway forward onto the board. |
| **Size** | 480 × 321 × 200 mm (w × h × d), about 1.8 kg |
| **Camera** | 8 MP (3840 × 2160) Sony STARVIS 2 sensor, locked-focus low-distortion M12 lens, 90° wide, 185 mm above the board and tilted 16° back toward the hive |
| **In view** | The bottom ≈ 35 mm of the hive wall, the porch and the landing board up to 15 mm from its front edge, ≈ 400 mm across. ≈ 9.5 px/mm on the board: a worker bee is ≈ 125 px long and a varroa mite ≈ 14 px |
| **Counting line** | The porch mouth, 40 mm in front of the hive: every bee in or out crosses it in view |
| **Compute** | Swappable sled: Raspberry Pi 5 (8 GB), Hailo-8 (26 TOPS) and 256 GB NVMe for now; a Jetson Orin NX or a later accelerator uses the same bay |
| **Supervisor** | Always-on ESP32-S3 board (the beehive-scale carrier design) that switches the computer on only when bees can fly |
| **Power** | PoE+ (802.3at), 12–24 V DC, or the solar version (10 W on the roof + 77 Wh LiFePO4) |
| **Links** | Ethernet (PoE), Wi-Fi, BLE for setup, M12 accessory port for the beehive scale |
| **Mounting** | An entrance plate held by 4 wood screws. The arch hangs on it and locks with 2 thumbscrews. The same arch fits the beehive scale (on risers) and the Robotic Beehive (on its entrance frame). |
| **Target BOM** | ≈ €350–450 at 100 units (Pi 5 + Hailo sled). ApicAI sells at €350–550. |

![Exploded view: roof, head with fins, compute sled and service face, camera module, side arms, entrance plate, landing board](preview.png)

## Design decisions

### 1. The camera looks down from a fixed place

The prototypes used a varifocal 4K camera on a wall bracket above the entrance. Each installation had a different angle and distance, so bee size, speed and the counting line changed from hive to hive, and the camera was sometimes knocked out of alignment.

- **185 mm above the board, tilted 16° toward the hive.** A 90° low-distortion lens keeps the arch low, and the calibration markers correct what distortion is left. The small tilt adds the porch roof and the bottom of the hive wall to the view (see [section 2](#2-flight-and-landing-where-to-count)). On the board the view is still close to top-down, so bees are seen in near-true proportions: pose keypoints, body length, pollen loads and mites are measurable, not just detectable. A fixed tilt beats a pivoting camera: no motor outdoors, and no calibration that drifts.
- **Locked optics.** A fixed M12 lens and a fixed working distance: every unit produces the same image, and models trained on one unit work on all of them.
- **The camera is a module.** The sensor board connects over MIPI CSI with its own flex cable. A global-shutter sensor, which pose analysis of fast wing and leg motion may need, can replace it without changing the housing.
- **Calibration markers on the board.** Four ArUco markers and a millimetre scale are in every frame. The software computes mm/px exactly, straightens the view, and raises an alert if the Observer has been knocked.

4K stays. A cheaper low-resolution SKU would lose mites and pose, the data quality the product is built for. If a budget version is needed, it should be the same arch with a smaller compute sled, not a worse camera.

![Field of view: the yellow pyramid covers the bottom of the hive wall, the porch and the board, inside the arms](preview-fov.png)

### 2. Flight and landing: where to count

Bees do not all land on the landing board. Some land on the hive wall and walk down into the entrance, especially at peak traffic, in wind, or when the board is small or steep. A camera that only sees the board would miss them, or see them appear at the entrance edge with no clear direction.

What matters is not where bees land but that every bee crosses one line the camera sees. So the design moves that line:

- **A porch moves the doorway onto the board.** A 40 mm deep, 15 mm high tunnel across the full 300 mm entrance, in the same matt grey as the board. A bee on the wall has to walk down onto the porch roof and step off its front edge onto the board to get in. Every bee in or out crosses the porch mouth, in full view, and the mouth is the counting line: a straight line on a flat board, the easiest case for a tracker.
- **The camera also sees the wall.** The 16° tilt adds the porch roof and the bottom ≈ 35 mm of the wall to the view. Bees that land on the wall are tracked from the moment they land, and the share of bees that land there is measured, not guessed.
- **Counting rule.** A track that ends inside the porch is *in*, a track that starts there is *out*, wherever it came from. Tracks that stay ambiguous are reported separately with a confidence value, not dropped (the telemetry already has `unknownDirection`).
- **Nothing to clean, nothing to light.** The porch is short and open-air, with no glass. It is shorter than the tunnels most electronic bee counters use, and guard bees tend to like a defined doorway. The entrance reducer slides in its roof.
- **Colours in view are chosen for detection.** The porch, the reducer and the entrance plate are matt grey. Nothing yellow or brown is in the view, so nothing looks like a bee. Bare aluminium is avoided because it throws glare.

Rejected alternatives:

- **An enclosed glass tunnel with the camera behind the glass.** It gives the cleanest counts per bee, but propolis, wax, dust and condensation build up on the glass. It needs constant lighting, creates congestion at peak traffic, gets in the way of fanning and ventilation, drones, the queen and bees carrying out the dead, and loses the open view that pollen, orientation-flight, guard and pose data depend on. It stays a research option.
- **A pivoting camera.** A motor and bearing outdoors, and a calibration that changes with every move, for no gain over a fixed tilt.
- **Discouraging bees from landing on the wall.** The porch already makes wall landing harmless for counting, so the bees keep their natural flight.

How much the porch costs the bees is not known yet and has to be measured (see the open questions at the end).

![What the camera sees: hive wall, porch roof with the reducer, counting line, board with markers](preview-installed.png)

### 3. Light, glare and rain

The arch is kept small on purpose. An earlier version had a full canopy over the whole board and closed side cheeks. It gave the most even light, but it was bulky and closed the entrance in. The current version protects what needs protecting (lens, head, electronics) and handles the light on the board in software and in the board itself.

- **Small ridged roof.** 480 × 150 mm of opal (light-diffusing) UV-stabilised polycarbonate, cold-bent into a shallow ridge over the head. It keeps sun and rain off the lens and head. Rain runs to the two side eaves and drips beside the board, outside the view, never onto the board in front of the camera. Because it is opal, its shadow on the board is faint and soft and does not cut bees in half in the image.
- **Matt light-grey board (≈ N7).** It is the background of every frame, so it is designed as part of the product. White overexposes in the sun and hides pale pollen loads. Wood grain and dirt confuse detectors. The top 3 mm insert slides out for washing.
- **Exposure for the board, not the scene.** The camera meters on the board area between the markers, with a short shutter time so bees in flight stay sharp. The auto-exposure profile is tuned for sun, cloud and shade on a known grey.
- **Downward-facing window.** The lens window is at the tip of a matt black hood and faces the ground. Rain cannot reach it, the sky cannot reflect in it, and the roof keeps the sun off it. A 0.3 W heater film clears dew on cold mornings.
- **Light bars, rarely used.** Two diffused LED bars have crossed polarisers on the LEDs and the lens to remove glints from shiny bees and wet pollen. They only flash in sync with the exposure, at dusk or in deep shade.
- **If glare shows up in the field**, clip-on side screens and a deeper roof can be added to the same arch without changing anything else.

### 4. Wires: none in the sun, none in view

- All cables enter from below, under the right arm, facing the ground: a PoE cable gland and an M12 accessory socket. Water runs off them, not into them, and the cable leaves with a drip loop.
- The right arm is a hollow box section. The harness runs up inside it to the head.
- The field of view ends inside the arms' inner faces. The arms, head, roof and cables are never in the video. The viewer's *Show what the camera sees* inset renders exactly what the lens sees.

### 5. Installation, service, manufacturing

- **Install once, hang in seconds.** The entrance plate (aluminium, powder-coated matt grey) is screwed to the bottom board with 4 stainless screws on either side of the entrance, using a paper drill template. Its window matches the 300 × 15 mm entrance, and it carries the porch. The arch hangs on the plate's two bent ears and locks with two captive thumbscrews. It comes off for an inspection, a hive move or winter in seconds, and goes back to exactly the same place.
- **Service side is +X**, the same as the scale pod. The compute sled slides out of the right arm after a quarter-turn. It has a status ring, a setup button and a USB-C port for copying full-resolution research clips on site.
- **Parts any workshop can make.** Laser-cut and folded aluminium arms and plate, an aluminium extrusion for the head (it is also the heatsink), a cut and cold-bent polycarbonate roof, and a CNC-routed HDPE board. Small parts (sled, risers, end caps) are 3D-printed ASA for pilot batches.
- **Flat-pack.** The arch ships as flat parts plus the head, in a box of about 500 × 250 × 110 mm. Assembly needs 8 captive screws and a screwdriver. The board folds up on its hinge.
- **No fan.** The head is the heatsink. Its fins sit in the open gap under the roof, where air flows freely front to back.

### 6. Works alone, works better together

The arch is identical in all three setups. Only what it hangs on changes.

| Setup | Mount | Power | Data |
| --- | --- | --- | --- |
| **Alone on a hive** | Entrance plate, 4 screws | PoE+ from a switch or injector (up to 100 m), 12–24 V DC, or the solar roof | Ethernet or Wi-Fi |
| **With the beehive scale** | Two printed risers hook onto the scale's front rail. The porch bridges the gap from the entrance over the deck to the board. The arch hangs on the scale base, not the hive, so its weight, bees on the board and snow on the roof are never weighed. | The Observer powers the scale pod over the M12 lead (5 V), so the scale needs no solar board | The scale sends weight and temperatures over UART; the Observer uploads both and syncs the time |
| **On the Robotic Beehive** | The robot's entrance tunnels end in the same ears | From the robot PoE switch, cable inside a corner post | The robot uses entrance activity to choose when to inspect. Heavy models (pose) can run on the robot's Jetson. |

The M12 accessory port has the same pinout as the scale's front connector: 5 V out, ground, 1-Wire, UART, wake, shield.

Interface requirement for the Robotic Beehive: the tunnel mouth must fit inside the arch and end in the porch (≤ 312 mm wide at the front, currently 480 mm).

![On the beehive scale: risers on the front rail, short M12 lead to the scale](preview-scale.png)

## Energy

The computer is the only large consumer. It runs only when bees can fly, and the always-on supervisor decides when that is.

| State | Draw | When |
| --- | --- | --- |
| Asleep | ≈ 0.12 W (supervisor, sensors, idle regulators) | Night, rain, below ≈ 10 °C, winter |
| Observing | ≈ 9 W (Pi 5 + Hailo-8 + 4K camera + Ethernet) | Flight weather, daylight |
| Booting | ≈ 5 W for ≈ 25 s | Before each observation in sampled mode |

The prototype Jetson Orin Nano measured 6.9 W at 720p. The 9 W figure assumes 4K capture and is an estimate until the Pi 5 + Hailo sled is measured.

| Mode | Energy per flight day (12 h) | Use |
| --- | --- | --- |
| Continuous | ≈ 111 Wh | PoE / mains: counts, tracks and clips all day |
| Sampled (2 of every 15 min) | ≈ 19 Wh | Solar: traffic curve with 13 % coverage, clips on anomalies |
| Asleep all day | ≈ 3 Wh | Rain, cold, winter |

**Solar version.** Two 5 W ETFE panels are laminated on the roof slopes (10 W). From May to August in Estonia they yield about 32 Wh/day (≈ 4.5 sun-hours on a near-horizontal panel, 70 % system efficiency), which covers the sampled mode (2 minutes in every 15, ≈ 19 Wh). Customers who want continuous recording without mains use PoE, or a separate panel on the M12 input. Energy demand follows the weather: bees fly when it is sunny and warm, which is when the panel produces. On rainy or cold days the Observer stays asleep at ≈ 3 Wh/day, so the 77 Wh LiFePO4 battery lasts about 3 weeks without sun. Flight weather without sun (warm and overcast) is the worst case: about 3.5 days of sampled observation from a full battery.

**PoE is the default** because it solves power and the unreliable apiary Wi-Fi seen in the field test with one outdoor cable. Pose models and 60 FPS research capture need continuous power anyway.

![Solar version: 10 W of panels on the roof, battery sled in the left bay](preview-solar.png)

## Competition

| | ApicAI (DE) | Beemate (AU) | Purple Hive (AU) | Gratheon Entrance Observer |
| --- | --- | --- | --- | --- |
| Focus | Pollination, counts | Counts, live stream | Varroa only | Counts, tracks, pollen, varroa, pose |
| Camera | Jetson at the entrance | HD | 2 cameras, 1 photo/s | 4K over wall, porch and board, locked optics, calibrated board, porch as counting line |
| Power | Mains / solar | Mains | Solar, 4G | PoE, or solar roof |
| Integration | Scale + sensors | — | — | Beehive scale (power + data), Robotic Beehive |
| Openness | Closed | Closed | Closed | Open source hardware and software |

## Open questions

- Measure the porch's cost to the bees: run two hives side by side on beehive scales, one with the porch and one without, and compare daily weight gain and forager traffic.
- Measure how many bees land on the wall at all, from the wall strip in view, over a season and at different traffic levels.
- Label clips by hand, with and without the porch, and compare against the automatic in/out counts.

- Measure Pi 5 + Hailo-8 with 4K capture, tracking and encoding at the same time: watts, FPS, thermal behaviour in the head at 35 °C ambient.
- Test bee acceptance of the arch over the landing board, and whether bees beard on the head in hot weather (bearding detection could be a feature).
- Global vs rolling shutter for pose: compare the two camera modules side by side on the same arch.
- Measure how much the roof shadow and direct sun on the board affect counts, and whether clip-on side screens are worth adding.
- Whether the board needs a clip-on entrance reducer (hornets, robbing).
