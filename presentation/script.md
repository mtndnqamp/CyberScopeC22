# CyberScope presentation script

Allow about four minutes before the live demo. Follow the bracketed cues without reading them aloud. The diagram loops, so you can explain each scenario at your own pace.

## Slide 1: CyberScope

We're the CyberScope team. We're investigating how changes to an IoT device affect trust in its sensor data. Our approach is to compare an integrity map of the device's current state with an approved baseline.

[Advance to Problem statement.]

## Slide 2: Problem statement

### Section 1: The problem and its impact

[Start with the headline, bullet points, connected-device diagram and CyberScope question visible.]

In a smart home, an industrial environment or an autonomous system, decisions depend on data coming from IoT devices.

Those devices are difficult to secure. The I2Map research describes how an attacker could change a device's hardware, software, network configuration or other settings without stopping it from operating.

We can no longer assume its data is trustworthy just because it still appears to work normally. The effects can reach the systems that depend on that device too.

### Section 2: The evidence and CyberScope's purpose

[Advance once to reveal both statistics and their source. Let the numbers finish counting before reading them.]

In its OT assessments and exercises, Dragos reported that 56 percent lacked visibility below the boundary between IT and operational technology. It also found that 88 percent struggled with detection and response. These figures are findings from those engagements, not a survey of all industrial control system owners.

CyberScope checks whether a device has moved away from its known trusted state.

We use the I2Map approach to collect selected device parameters and compare the current state with an approved baseline. This lets us identify changes before relying on the device's data.

[Advance to Design & methodology.]

## Slide 3: Design & methodology

### Collect, hash, compare, decide

Our test device is a physical Raspberry Pi running the CyberScope client. The design uses three separate hosts for the client, the verifier and the blockchain. We use Python on the Pi to collect selected hardware, software, network and configuration parameters. The environmental parameters we can monitor depend on the measurements available.

We then hash the collected values with SHA-256 to produce an integrity map, or I2Map. Hashing produces a digest; it doesn't encrypt the values.

### Scenario 1: Onboard and accept

[Select Scenario 1: Onboard & accept. Let it loop while explaining.]

First, the administrator approves a device configuration known to be legitimate. The Raspberry Pi collects its parameters and generates the Base I2Map, our trusted reference. It sends that baseline to Host 3, where a Solidity smart contract stores it on a private Ethereum-compatible blockchain.

Once the device is operating, the Pi collects its parameters again and generates a runtime I2Map using SHA-256. It sends that map to the blockchain on Host 3. The blockchain then passes the runtime I2Map and the approved baseline to the verifier on Host 2, where the two digests are compared.

If the runtime digest matches the baseline, the monitored state hasn't changed. In this proposed flow, the verifier releases the sensor data to the consumer. The check only covers the parameters we monitor, so a match doesn't guarantee that every sensor reading is accurate.

### Scenario 2: Reject and restore

[Select Scenario 2: Reject & restore. Let it loop while explaining.]

Here, connecting an unauthorised USB device changes a monitored parameter. The Pi generates a new I2Map and sends it to the blockchain. The blockchain passes it to the verifier alongside the baseline. The verifier detects the mismatch, rejects the sensor data and alerts the administrator.

The administrator then restores the approved configuration. The Pi generates another runtime I2Map, sends it to the blockchain, and the blockchain passes it to the verifier for another comparison. Once the digest matches, the verifier can accept data again. Throughout this scenario, the original baseline on the chain stays the same.

### Implementation, validation and demo handover

What you're seeing is the architecture we're working towards. The repository contains Python integrity checks and a contract that stores and retrieves hashes. We still need to bring those components together for the full flow from the Raspberry Pi to the blockchain and then to the verifier.

To test the integrated system, we'll deliberately change software, network settings and configuration, and connect an unauthorised USB device. To measure false positives, we'll repeat checks without changing the device. We'll also record execution time, transaction commit time and memory usage.

We'll now show the prototype's current behaviour in the live demo.

[Switch to the live demo.]
