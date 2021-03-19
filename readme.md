# MQTT Label Server

This software provides an MQTT interface to a set of usb-connected Brother QL label printers attached to a linux computer.  

* Python >= 3.7
* Uses the `brother_ql` python package
* Connects to a single MQTT broker and performs all communication through it

## Overview

The goal of this software is to provide a scalable backend for Brother QL label printers.

We have services which rely on the label printers, and have encountered a few issues in using them:
1. For whatever reason, the WIFI is unreliable at our office when a non-wifi system has to initiate communication with the wifi label printer
2. There isn't any obvious way to scale out the printers, since a central system has to know about them and maintain knowledge of their addresses
3. We don't really have a way of getting status info about the printers
4. IP addresses are going to become tight

## System Theory of Operation

The system is composed of two parts:
1. A scalable number of label servers, each being a linux machine with a number of USB connected printers
2. A central management server, which is an ephemeral service through which all consuming services make their printing requests

These are connected through the MQTT broker and pre-agreed topic names

### Label Server
* Label server host (the linux machine) starts the software service
* Checks what printers are attached
* Connects to MQTT broker
* Begins regularly publishing information on the connected printing devices
* Subscribes to command topics
* Performs commands as they are received

Concerns:
* Label printer is a single threaded resource, needs to be protected by some sort of queue
* Keep label server as simple as possible: changes here need to be deployed everywhere

### Central Manager
* Add all complexity here
* Maintain a list of unique printer serial numbers, and be able to assign aliases to them
