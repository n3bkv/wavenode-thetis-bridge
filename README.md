# WaveNode to Thetis LP100A Bridge

A small Python bridge that takes WaveNode MQTT telemetry and sends it to Thetis as LP100A-style UDP/XML meter data.

This is intended for experimenting with Thetis **Multi Meter I/O** using WaveNode forward power, reflected power and SWR values.

## What it does

```text
WaveNode MQTT topics
        ↓
Python bridge
        ↓
LP100A-style UDP XML packets
        ↓
Thetis Multi Meter I/O
```

The bridge subscribes to WaveNode MQTT topics such as:

```text
wavenode/avg_watts/1
wavenode/ref_watts/avg/1
wavenode/swr1
```

It then sends XML packets using an LP100A-like structure:

```xml
<LP100A>
  <fwdpwr>100.00</fwdpwr>
  <refpwr>2.00</refpwr>
  <swr>1.20</swr>
  <z>50.00</z>
  <phase>0.00</phase>
  <peakpwr>100.00</peakpwr>
</LP100A>
```

## Status

Experimental / proof of concept.

This was created based on inspection of LP100A UDP/XML bridge behavior and is intended to be tested with Thetis. The exact Thetis behavior may vary by version and configuration.

## Requirements

- Python 3.8 or newer
- Network access to the WaveNode MQTT broker
- Network access to the computer running Thetis
- The Python package `paho-mqtt`

Install dependencies:

```bash
pip install -r requirements.txt
```

Or:

```bash
pip install paho-mqtt
```

## Thetis setup

In Thetis, configure Multi Meter I/O for external meter input:

```text
Protocol: UDP
Direction: In
Format: XML
Port: 9388
```

If running the bridge on the same Windows PC as Thetis, send to:

```text
127.0.0.1:9388
```

If running the bridge on another machine, send to the IP address of the Thetis PC.

## Basic usage

Example:

```bash
python wavenode_to_thetis_lp100a.py \
  --mqtt-host 192.168.1.10 \
  --thetis-host 192.168.1.25 \
  --thetis-port 9388 \
  --sensor 1
```

Replace:

- `192.168.1.10` with the IP address of your MQTT broker
- `192.168.1.25` with the IP address of the PC running Thetis
- `--sensor 1` with the WaveNode sensor you want to send to Thetis

## Running on Windows

1. Install Python 3 from <https://www.python.org/downloads/windows/>
2. Open Command Prompt or PowerShell
3. Install the dependency:

```powershell
pip install paho-mqtt
```

4. Run the bridge:

```powershell
python wavenode_to_thetis_lp100a.py --mqtt-host 192.168.1.10 --thetis-host 127.0.0.1 --sensor 1
```

Using `127.0.0.1` is recommended when the bridge and Thetis are running on the same PC.

## Running on Raspberry Pi / Linux

```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install paho-mqtt
python3 wavenode_to_thetis_lp100a.py --mqtt-host 192.168.1.10 --thetis-host 192.168.1.25 --sensor 1
```

## Command line options

```text
--mqtt-host        MQTT broker host/IP. Default: 192.168.1.10
--mqtt-port        MQTT broker port. Default: 1883
--mqtt-username    Optional MQTT username
--mqtt-password    Optional MQTT password
--thetis-host      IP address of the Thetis PC. Required.
--thetis-port      Thetis UDP XML input port. Default: 9388
--base-topic       Base MQTT topic. Default: wavenode
--sensor           WaveNode sensor number. Default: 1
--interval         UDP send interval in seconds. Default: 0.5
--zero-after       Zero meters after N seconds with no updates. Default: 5.0. Use 0 to disable.
--send-on-update   Also send immediately when MQTT updates arrive
--verbose          Print each UDP send
```

## Auto-zero behavior

By default, if no matching WaveNode updates are received for 5 seconds, the bridge sends:

```text
Forward power = 0
Reflected power = 0
SWR = 1.0
```

You can change that timeout:

```bash
python wavenode_to_thetis_lp100a.py --mqtt-host 192.168.1.10 --thetis-host 127.0.0.1 --zero-after 10
```

Or disable it:

```bash
python wavenode_to_thetis_lp100a.py --mqtt-host 192.168.1.10 --thetis-host 127.0.0.1 --zero-after 0
```

## Troubleshooting

### Thetis does not show meter data

- Confirm Thetis Multi Meter I/O is set to UDP / In / XML.
- Confirm the port matches the script, usually `9388`.
- If running on a different machine, check the Windows firewall on the Thetis PC.
- Try running the bridge on the same PC as Thetis and use `--thetis-host 127.0.0.1`.
- Run the script with `--verbose` to confirm it is sending packets.

### MQTT connects but values do not update

- Confirm the MQTT broker IP and port.
- Confirm the WaveNode topics match your sensor number.
- Try using an MQTT client such as MQTT Explorer to verify topic names.

## Notes

This bridge does not make Thetis an MQTT client. The bridge is the translator:

```text
MQTT from WaveNode → UDP/XML to Thetis
```

## License

MIT License. See `LICENSE`.


## Support This Project

If you find this useful, star ⭐ the repo! It helps others discover it.


## More Info

Blog: https://hamradiohacks.blogspot.com

GitHub: https://github.com/n3bkv
