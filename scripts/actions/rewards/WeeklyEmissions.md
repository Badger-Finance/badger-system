# Weekly Emissions Script

### Start Time
Set the 'start' time variable to the apporpriate point.
Weekly emission schedules are set in active_emissions.py
Note that this is set *in your local time zone*. This would be a good PR to normalize it as UTC time.

Historically, the schedules start at 1pm EST on Thursdays. They should be back-to-back, with the new one starting right as the previous one ends.
The logging output after the run will show the times for manual verification.

Watch out for daylight savings time shift!

### Emissions Data
The data is read from the [emissions spreadsheet](https://docs.google.com/spreadsheets/d/1m117bYDkXe9lO5sY5gW70F_q2YmxgLIelG-PiD72S4s/edit#gid=2123991267).

Note that for the "native asset" Setts (Badger, Digg, and their respective LPs) we set the unlock schedule to _half_ the amount stated in the document.
This is because half of these rewards are auto-compounding and handled through a different emission schedule manager. Combining these two would be a good PR.