#!/usr/bin/env python3
"""
Create detailed schedules for each witch showing complete timeline:
- Departure times
- Travel times
- Collection times
- Unload times
- Account for ALL tickets with proper travel time calculations
"""

import json
from datetime import datetime, timedelta

# Load data
print("Loading data...")
with open('cauldrons.json', 'r') as f:
    cauldrons_data = json.load(f)

with open('transport_tickets.json', 'r') as f:
    tickets_data = json.load(f)

cauldrons = {c['id']: c for c in cauldrons_data['cauldrons']}
network_edges = cauldrons_data['network']['edges']
tickets = tickets_data['transport_tickets']

# Build travel time lookup
travel_times = {}
for edge in network_edges:
    key = (edge['from'], edge['to'])
    travel_times[key] = edge['travel_time_minutes']
    travel_times[(edge['to'], edge['from'])] = edge['travel_time_minutes']

def get_travel_time(from_id, to_id):
    """Get travel time between two locations"""
    if from_id == to_id:
        return 0
    return travel_times.get((from_id, to_id), 30)  # Default 30 min if not found

# Constants
UNLOAD_TIME = 15  # Minutes to unload at market

# Parse tickets and group by witch
print("\nParsing tickets and creating schedules...")
tickets_by_witch = {}
for ticket in tickets:
    witch_id = ticket.get('courier_id', 'unknown')
    if witch_id not in tickets_by_witch:
        tickets_by_witch[witch_id] = []
    
    start = datetime.fromisoformat(ticket['collection_start_timestamp'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(ticket['collection_timestamp'].replace('Z', '+00:00'))
    collection_duration = (end - start).total_seconds() / 60
    
    tickets_by_witch[witch_id].append({
        'ticket_id': ticket['ticket_id'],
        'cauldron_id': ticket['cauldron_id'],
        'collection_start': start,
        'collection_end': end,
        'collection_duration': collection_duration,
        'amount': ticket.get('amount_collected', 0)
    })

# Sort tickets by start time for each witch
for witch_id in tickets_by_witch:
    tickets_by_witch[witch_id].sort(key=lambda x: x['collection_start'])

# Create detailed schedules
detailed_schedules = {}

for witch_id, ticket_list in tickets_by_witch.items():
    schedule_entries = []
    current_location = 'market_001'  # Start at market
    
    for i, ticket in enumerate(ticket_list):
        cauldron_id = ticket['cauldron_id']
        
        # Calculate travel times
        travel_to_cauldron = get_travel_time(current_location, cauldron_id)
        travel_to_market = get_travel_time(cauldron_id, 'market_001')
        
        if i == 0:
            # First ticket - calculate departure from market
            # Want to arrive at cauldron at collection_start
            departure_from_market = ticket['collection_start'] - timedelta(minutes=travel_to_cauldron)
            arrival_at_cauldron = ticket['collection_start']
        else:
            # Subsequent tickets - need to check when witch finishes previous task
            prev_entry = schedule_entries[-1]
            prev_unload_complete = datetime.fromisoformat(prev_entry['unload_complete'].replace('Z', '+00:00'))
            
            # Calculate when witch can arrive at next cauldron
            earliest_arrival = prev_unload_complete + timedelta(minutes=travel_to_cauldron)
            
            # Must arrive before or at collection start
            if earliest_arrival <= ticket['collection_start']:
                arrival_at_cauldron = ticket['collection_start']
                departure_from_market = ticket['collection_start'] - timedelta(minutes=travel_to_cauldron)
            else:
                # If we can't make it on time, arrive as soon as possible
                arrival_at_cauldron = earliest_arrival
                departure_from_market = prev_unload_complete
        
        # Collection times
        collection_start = arrival_at_cauldron
        collection_end = collection_start + timedelta(minutes=ticket['collection_duration'])
        
        # Travel back to market
        departure_from_cauldron = collection_end
        arrival_at_market = departure_from_cauldron + timedelta(minutes=travel_to_market)
        
        # Unload at market
        unload_start = arrival_at_market
        unload_complete = unload_start + timedelta(minutes=UNLOAD_TIME)
        
        # Create detailed schedule entry
        schedule_entry = {
            'ticket_id': ticket['ticket_id'],
            'cauldron_id': cauldron_id,
            'amount_collected': ticket['amount'],
            'departure_from_market': departure_from_market.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'travel_to_cauldron_minutes': travel_to_cauldron,
            'arrival_at_cauldron': arrival_at_cauldron.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'collection_start': collection_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'collection_duration_minutes': ticket['collection_duration'],
            'collection_end': collection_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'departure_from_cauldron': departure_from_cauldron.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'travel_to_market_minutes': travel_to_market,
            'arrival_at_market': arrival_at_market.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'unload_start': unload_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'unload_duration_minutes': UNLOAD_TIME,
            'unload_complete': unload_complete.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'ready_for_next_task': unload_complete.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        schedule_entries.append(schedule_entry)
        current_location = 'market_001'  # After unloading, witch is at market
    
    detailed_schedules[witch_id] = {
        'total_tickets': len(schedule_entries),
        'schedule': schedule_entries
    }

# Create output structure
output = {
    'metadata': {
        'created_date': datetime.now().isoformat(),
        'total_witches': len(detailed_schedules),
        'total_tickets': sum(len(s['schedule']) for s in detailed_schedules.values()),
        'unload_time_minutes': UNLOAD_TIME,
        'note': 'Complete schedules for all witches showing all travel, collection, and unload times. All tickets are accounted for.'
    },
    'witch_schedules': detailed_schedules
}

# Save detailed schedules
output_file = 'detailed_witch_schedules.json'
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Created detailed schedules in {output_file}")
print(f"\nSummary:")
print(f"  Total witches: {len(detailed_schedules)}")
print(f"  Total tickets scheduled: {output['metadata']['total_tickets']}")

for witch_id, schedule_info in detailed_schedules.items():
    print(f"  {witch_id}: {schedule_info['total_tickets']} tickets")
    if schedule_info['schedule']:
        first = schedule_info['schedule'][0]
        last = schedule_info['schedule'][-1]
        print(f"    First task: {first['ticket_id']} - departs {first['departure_from_market'][:16]}")
        print(f"    Last task: {last['ticket_id']} - completes {last['unload_complete'][:16]}")

print("\n" + "=" * 70)
print("Schedule includes for each ticket:")
print("  - Departure from market (or previous location)")
print("  - Travel time to cauldron")
print("  - Arrival at cauldron")
print("  - Collection start/end times")
print("  - Travel time to market")
print("  - Arrival at market")
print("  - Unload start/complete times")
print("  - Ready for next task time")
print("=" * 70)

