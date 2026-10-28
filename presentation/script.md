# CyberScope video script

Allow approximately one minute each for problem statement and scope, architecture, and demo. Each section has two speakers with a maximum of 30 seconds each; the scripted parts contain fewer than 60 words, so rehearse with a timer and leave room for pauses. Bracketed cues are not spoken.

## Problem statement and scope (approximately 1 minute)

### Speaker 1: Problem statement (approximately 30 seconds)

[Show the CyberScope title, then the Problem statement slide.]

We're the CyberScope team, and our project addresses the risk of trusting data from an IoT device whose configuration has changed. In smart homes, industrial environments and autonomous systems, an attacker could alter a device's software, hardware or network settings while it continues operating, affecting the systems that rely on its data.

### Speaker 2: Scope (approximately 30 seconds)

CyberScope checks whether selected parameters on a Raspberry Pi still match an approved baseline, using the I2Map approach to represent the device's state. Our scope covers monitored hardware, software, network and configuration changes; a matching hash shows those monitored values are unchanged, but it cannot guarantee the accuracy of every sensor reading.

[Advance to Design & methodology.]

## Architecture (approximately 1 minute)

### Speaker 3: Architecture and baseline (approximately 30 seconds)

[Show the architecture diagram and select Scenario 1: Onboard & accept.]

The design separates the Raspberry Pi client, verifier and blockchain across three hosts, with Python collecting the Pi's selected parameters. After an administrator approves the device configuration, SHA-256 hashing produces the Base I2Map, which becomes the trusted baseline stored through a Solidity smart contract on a private Ethereum-compatible blockchain.

### Speaker 4: Runtime verification (approximately 30 seconds)

[Select Scenario 2: Reject & restore.]

In the proposed flow, runtime parameters are hashed again and compared with the approved baseline by the verifier. A match allows data through; a mismatch, such as after USB insertion, triggers rejection and an administrator alert, while restoring the approved configuration allows another check without changing the baseline.

## Demo (1 minute reserved)

[Switch to the live demo. Speakers 5 and 6 have a maximum of 30 seconds each; no demo narration was present in the original script.]
