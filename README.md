# Philips SICP for Home Assistant

A [HACS](https://hacs.xyz/) custom integration for controlling Philips
professional/signage displays over **SICP** (Serial Interface
Communication Protocol) - TCP port 5000 by default.

Talks to the display protocol directly with a small built-in asyncio TCP
client. It does not depend on any third-party device library.

## Highlights

- **No external device library.** The SICP framing/checksum/addressing
  (see `custom_components/philips_sicp/protocol.py`) is implemented
  directly from *The SICP Commands Document V2.10*.
- **Multiple displays over one connection.** SICP addresses displays by
  Monitor ID. A LAN-connected display can forward SICP commands to other
  displays RS232-daisy-chained behind it (see the display's "SICP Serial
  Port Forwarding" setting). This integration lets you register one host
  and then add as many Monitor IDs as you have displays on that chain -
  each one becomes its own Home Assistant device, sharing the one TCP
  connection.
- **Auto-detected feature support.** Rather than hard-coding which SICP
  version or display platform supports which command, this integration
  probes every command once at startup and uses the protocol's own "NAV"
  (not supported) response to decide what to expose. Entities only show
  up for commands your specific display actually implements.
- **Broad command coverage.** Power, input source, volume/audio, PIP,
  picture/color adjustment, tiling, frame compensation, image rotation,
  date/time, scheduling, an LED-strip light entity, and various
  maintenance actions (restart, screenshot, factory reset, firmware
  upgrade, IP configuration) - the latter three exposed as opt-in
  services or disabled-by-default buttons since they are destructive or
  can strand a display off the network if misused.

## Installation

### Via HACS (custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Add `https://github.com/bfulham/ha-philips-sicp`, category **Integration**.
3. Install **Philips SICP**, then restart Home Assistant.

### Manual

Copy `custom_components/philips_sicp` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

Settings → Devices & Services → **Add Integration** → *Philips SICP*.

1. Enter the IP address (and port, default `5000`) of the LAN-connected
   display.
2. Add a Monitor ID for each display on that connection - the
   LAN-connected one, plus any RS232-daisy-chained behind it. Each is
   validated live against the display before being accepted. Group ID
   `0` addresses by Monitor ID directly (the normal case).

Add more displays later, or set the PIN used by the "Open Admin Menu"
button, from the integration's **Configure** options.

## Entities

Each display gets:

- A **media_player** for power, input source, volume and mute.
- **sensor** / **binary_sensor** entities for read-only status (model,
  firmware/SICP version, serial number, operating hours, temperature,
  video signal present, IP configuration, ...).
- **select** / **number** / **switch** entities for every SICP command
  your display reports supporting (power saving modes, picture
  adjustments, tiling, scheduling-adjacent settings, control locks,
  etc).
- A **light** entity for the RGB LED strip on `10BDLxx51T`-family
  displays, if present.
- **button** entities for one-shot actions (restart, screenshot, VGA
  auto-adjust, open admin menu). Factory reset, clear storage, and
  firmware upgrade are also buttons but are **disabled by default** -
  enable them deliberately in the entity registry if you want them.

## Services

A few commands are exposed as services instead of entities, either
because they don't fit a single-value entity (an ordered priority list)
or because misusing them has serious consequences:

- `philips_sicp.send_remote_key` - simulate a remote control key press.
- `philips_sicp.set_ip_parameter` - change IP/subnet/gateway/DNS. **Can
  strand the display off the network if misused.**
- `philips_sicp.set_monitor_id` - re-address a display. **The
  integration will stop being able to reach it under its old ID.**
- `philips_sicp.set_failover_priority` - set the ordered failover source list.
- `philips_sicp.reset_scheduler` - reset one or all scheduler pages.

## Disclaimer

Reverse-engineered from the vendor's own SICP protocol document.
Command coverage has been checked against the spec's worked byte
examples but has not yet been validated end-to-end against physical
hardware for every command - please open an issue if something
misbehaves on your display/platform/firmware combination.

## License

MIT - see [LICENSE](LICENSE).
