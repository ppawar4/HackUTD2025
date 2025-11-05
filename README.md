# CauldronWatch: The Potion Flow Monitoring Challenge

Deep within Poyo's Potion Factory, dozens of enchanted cauldrons bubble away, collecting potions from brewing towers spread across the facility. Each cauldron fills at its own pace before courier witches swoop in to haul the precious brews to the Enchanted Market. Every collection is logged using Potion Transport Tickets detailing how much potion was collected and when the journey finished.

But lately, something's amiss! Potion volumes don't quite match the transport tickets, and rumors of unlogged potion drains are spreading through the halls.

Your task is to develop a real-time Potion Flow Monitoring Dashboard that tracks potion levels across all cauldrons, identifies collection events, and checks the Potion Transport Tickets to detect any missing or unlogged potion. The system should automatically flag inconsistencies, identify suspicious activity, and help ensure every drop of potion is properly accounted for.

You'll receive historical and real-time cauldron level data, Potion Transport Ticket records, and a map of the potion network linking each cauldron to the Enchanted Market. Use these to visualize the entire operation, monitor live potion flows, and test your real-time detection logic.

✨ Bonus: Extend your system to forecast brew levels and optimize courier routes — helping witches plan efficient pickup schedules, prevent cauldron overflows, and keep the potion trade flowing smoothly across the realm.

## 📌 Additional Information

### Input Data

- **List of Cauldrons**: Each cauldron has a unique ID, a name, a latitude/longitude, and a maximum storage volume. 
- **Potion Network Map**: Includes all cauldrons as nodes with their locations, and edges representing travel paths with travel times. The map also contains the Enchanted Market. This map is used to find an optimized schedule for the witches to ensure no cauldron ever overflows, accounting for the travel time between cauldrons and to the Enchanted Market.
- **Potion Transport Tickets**: Tickets are received at the end of each day and contain only a date. Each ticket records the amount of potion collected and transported. 
- **Historical Cauldron Level Data**: Minute-by-minute potion volumes for each cauldron, covering approximately one week. This data shows how potion levels change over time, including the effects of continuous filling and periodic draining.

### Expected Output

Your solution should provide:

- **Visualization of the Potion Network**: A map displaying all cauldrons, potion levels, and the sales point.
- **Historic Data Playback**: Ability to review historical potion levels and transport ticket activity.
- **Real-Time Monitoring**: Live feed of potion levels in all cauldrons as new data arrives.
- **Discrepancy Detection**: Since tickets arrive at the end of the day with only dates (no timestamps), you must match tickets to the actual drain events that occurred during that day. Verify that the volumes on the tickets match the drains for that day by comparing ticket volumes (which include level change + potion generated during drain) to the actual drain events recorded in the historical data. Identify any tickets that appear to have transported more or less than what left the cauldron, highlighting potential unlogged potion drains or discrepancies.

### Things to Keep in Mind

- **Continuous Potion Flow During Drainage**: While potion is being drained from a cauldron, more potion continues to accumulate into the tank at the cauldron's fill rate. This means the total volume collected includes both the level change and the potion generated during the drain period.
- **Unload Time**: Witches take 15 minutes to unload each time they arrive at the market. This must be accounted for when scheduling multiple trips.
- **Per-Cauldron Rates**: Each cauldron has its own unique fill rate and drain rate, which can differ significantly between cauldrons. These rates determine how quickly potion accumulates and how quickly it can be collected.

### Bonus Output

**Optimized Courier Routes & Forecasting**: Using the potion network map, determine what is the minimum number of witches that can run the whole operation. Predict cauldron fill levels and generate efficient courier routes that prevent overflow while accounting for all these factors. Create an optimal schedule for the minimum number of witches required to maintain the entire operation. Visualize these routes on the map to ensure timely deliveries and prevent cauldron overflow.

## Checkout our Workshop!

**Intro to React Development: Your First Web Application** at 5:30pm on Saturday!

