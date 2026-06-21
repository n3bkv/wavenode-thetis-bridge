#!/usr/bin/env python3
"""
WaveNode MQTT to Thetis LP100A UDP/XML Bridge

Subscribes to WaveNode MQTT topics and sends LP100A-style UDP XML packets
for use with Thetis Multi Meter I/O.
"""

import argparse
import math
import socket
import threading
import time
from xml.sax.saxutils import escape

import paho.mqtt.client as mqtt


state = {
    "fwdpwr": 0.0,
    "refpwr": 0.0,
    "swr": 1.0,
    "peakpwr": 0.0,
    "last_update": 0.0,
}

lock = threading.Lock()


def dbm_from_watts(watts: float) -> float:
    """Convert watts to dBm."""
    if watts <= 0:
        return 0.0
    return 10.0 * math.log10(watts * 1000.0)


def build_lp100a_xml(sender: str, author: str, sw_version: str, swr_alarm: float) -> str:
    """Build an LP100A-style XML packet for Thetis Multi Meter I/O."""
    with lock:
        fwd = float(state["fwdpwr"])
        ref = float(state["refpwr"])
        swr = float(state["swr"])
        peak = max(float(state["peakpwr"]), fwd)
        state["peakpwr"] = peak

    high_swr = "true" if swr >= swr_alarm else "false"

    return f"""<?xml version="1.0" encoding="utf-8"?>
<LP100A>
  <fwdpwr>{fwd:.2f}</fwdpwr>
  <refpwr>{ref:.2f}</refpwr>
  <swr>{swr:.2f}</swr>
  <z>50.00</z>
  <phase>0.00</phase>
  <dbm>{dbm_from_watts(fwd):.2f}</dbm>
  <r>50.00</r>
  <x>0.00</x>
  <highswr>{high_swr}</highswr>
  <peakpwr>{peak:.2f}</peakpwr>
  <sender>{escape(sender)}</sender>
  <author>{escape(author)}</author>
  <sw-version>{escape(sw_version)}</sw-version>
  <comport>MQTT</comport>
  <demomode>false</demomode>
  <swralarmsetting>{swr_alarm:.2f}</swralarmsetting>
  <powermode>Average</powermode>
  <powermodeInt>0</powermodeInt>
</LP100A>"""


def send_udp(sock: socket.socket, host: str, port: int, args) -> None:
    xml = build_lp100a_xml(
        sender=args.sender,
        author=args.author,
        sw_version=args.sw_version,
        swr_alarm=args.swr_alarm,
    )
    sock.sendto(xml.encode("utf-8"), (host, port))
    if args.verbose:
        with lock:
            print(
                f"Sent fwd={state['fwdpwr']:.2f}W "
                f"ref={state['refpwr']:.2f}W swr={state['swr']:.2f} "
                f"to {host}:{port}"
            )


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(userdata["base_topic"] + "/#")
        print(f"Subscribed to {userdata['base_topic']}/#")
    else:
        print(f"MQTT connection failed: rc={rc}")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        value = float(msg.payload.decode("utf-8", errors="replace").strip())
    except Exception:
        return

    with lock:
        if topic == userdata["fwd_topic"]:
            state["fwdpwr"] = value
            state["peakpwr"] = max(state["peakpwr"], value)
        elif topic == userdata["ref_topic"]:
            state["refpwr"] = value
        elif topic == userdata["swr_topic"]:
            state["swr"] = value
        else:
            return

        state["last_update"] = time.time()

    if userdata["args"].send_on_update:
        send_udp(userdata["sock"], userdata["args"].thetis_host, userdata["args"].thetis_port, userdata["args"])


def periodic_sender(args, sock: socket.socket):
    while True:
        now = time.time()

        with lock:
            age = now - state["last_update"] if state["last_update"] else 999999
            if args.zero_after > 0 and age > args.zero_after:
                state["fwdpwr"] = 0.0
                state["refpwr"] = 0.0
                state["swr"] = 1.0

        send_udp(sock, args.thetis_host, args.thetis_port, args)
        time.sleep(args.interval)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bridge WaveNode MQTT data to Thetis LP100A-style UDP XML."
    )

    parser.add_argument("--mqtt-host", default="192.168.1.10", help="MQTT broker host/IP")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt-username", default=None, help="Optional MQTT username")
    parser.add_argument("--mqtt-password", default=None, help="Optional MQTT password")

    parser.add_argument("--thetis-host", required=True, help="IP address of the Thetis PC")
    parser.add_argument("--thetis-port", type=int, default=9388, help="Thetis UDP XML input port")

    parser.add_argument("--base-topic", default="wavenode", help="Base MQTT topic")
    parser.add_argument("--sensor", default="1", help="WaveNode sensor number: 1, 2, 3, etc.")

    parser.add_argument("--interval", type=float, default=0.5, help="UDP send interval in seconds")
    parser.add_argument("--zero-after", type=float, default=5.0, help="Zero meters after N seconds without updates; 0 disables")
    parser.add_argument("--send-on-update", action="store_true", help="Also send UDP immediately when a meter MQTT update arrives")

    parser.add_argument("--sender", default="WaveNode-MQTT-Bridge")
    parser.add_argument("--author", default="N3BKV")
    parser.add_argument("--sw-version", default="0.1.0")
    parser.add_argument("--swr-alarm", type=float, default=3.0)
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args()


def main():
    args = parse_args()

    base = args.base_topic.rstrip("/")
    fwd_topic = f"{base}/avg_watts/{args.sensor}"
    ref_topic = f"{base}/ref_watts/avg/{args.sensor}"
    swr_topic = f"{base}/swr{args.sensor}"

    print("WaveNode → Thetis LP100A UDP/XML Bridge")
    print("Using MQTT topics:")
    print(f"  FWD: {fwd_topic}")
    print(f"  REF: {ref_topic}")
    print(f"  SWR: {swr_topic}")
    print(f"Sending UDP XML to {args.thetis_host}:{args.thetis_port}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    userdata = {
        "args": args,
        "sock": sock,
        "base_topic": base,
        "fwd_topic": fwd_topic,
        "ref_topic": ref_topic,
        "swr_topic": swr_topic,
    }

    client = mqtt.Client(userdata=userdata)
    if args.mqtt_username:
        client.username_pw_set(args.mqtt_username, args.mqtt_password)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(args.mqtt_host, args.mqtt_port, 60)
    client.loop_start()

    try:
        periodic_sender(args, sock)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        client.loop_stop()
        client.disconnect()
        sock.close()


if __name__ == "__main__":
    main()
