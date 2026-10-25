# C3 replay messages v0
Use the four message types in `docs/trackb/MESSAGES.md`: rain_update, reservoir_update, twin_update, alert. Every message carries schema version and source=`replay|live|simulated`; preserve event/acquisition time and distinguish missing data from zero.
