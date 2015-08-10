# energy-statistics

This simple python script queries the EnerGenie EGM-PWM-LAN (http://energenie.com/item.aspx?id=6736),
parses the HTML output and logs the values to a log file.

Optionally sends emails which inform the receiver

* of the amount of energy which was consumed within a certain period of time.
* that the energy counter jumped to zero.
