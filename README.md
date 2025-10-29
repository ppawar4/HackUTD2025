# CauldronWatch: The Potion Flow Monitoring Challenge

Deep within Poyo’s Potion Factory, dozens of enchanted cauldrons bubble away, collecting potions from brewing towers spread across the facility. Each cauldron fills at its own pace before courier witches swoop in to haul the precious brews to the Enchanted Market. Every collection is logged using Potion Transport Tickets detailing how much potion was collected and when the journey finished.

But lately, something’s amiss! Potion volumes don’t quite match the transport tickets, and rumors of unlogged potion drains are spreading through the halls.

Your task is to develop a real-time Potion Flow Monitoring Dashboard that tracks potion levels across all cauldrons, identifies collection events, and checks the Potion Transport Tickets to detect any missing or unlogged potion. The system should automatically flag inconsistencies, identify suspicious activity, and help ensure every drop of potion is properly accounted for.

You’ll receive historical and real-time cauldron level data, Potion Transport Ticket records, and a map of the potion network linking each cauldron to the Enchanted Market. Use these to visualize the entire operation, monitor live potion flows, and test your real-time detection logic.

✨ Bonus: Extend your system to forecast brew levels and optimize courier routes — helping witches plan efficient pickup schedules, prevent cauldron overflows, and keep the potion trade flowing smoothly across the realm.


## 📌 Additional Information
### Input Data

List of Cauldrons: Each cauldron has a unique ID, a name, a latitude/longitude, and a maximum storage volume.
Potion Network Map: Includes all cauldrons as nodes with their locations, and edges representing broomstick travel paths with travel times. The map also contains the Enchanted Market.
Potion Transport Tickets: Each ticket records a finished timestamp and the amount of potion collected and transported.
Historical Cauldron Level Data: Minute-by-minute potion volumes for each cauldron, covering approximately one week.
Real-Time Potion Feed (Optional): A websocket stream providing live potion level updates for each cauldron every minute.


### Expected Output
Your solution should provide:

Visualization of the Potion Network: A map displaying all cauldrons, potion levels, and the sales point.
Historic Data Playback: Ability to review historical potion levels and transport ticket activity.
Real-Time Monitoring: Live feed of potion levels in all cauldrons as new data arrives.
Discrepancy Detection: Identification of potion transport tickets that appear to have transported more or less than what left the cauldron, highlighting potential unlogged potion drains.


### Bonus Output

Optimized Courier Routes & Forecasting: Create a strategy for future potion collection by predicting cauldron fill levels and generating efficient courier routes. Visualize these routes on the map to ensure timely deliveries and prevent cauldron overflow.
