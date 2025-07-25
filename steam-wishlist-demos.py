import time
from enum import Enum
import shutil
import webbrowser

import FreeSimpleGUI as sg
import requests

#from steam_web_api import Steam
#steam = Steam()

# TODO:
# Handle specific response status codes!

#================================================================================

class State(Enum):
  def __str__(self): return str(self.name)
  Available = 0
  Installed = 1
  Tried = 2
  Missing = 3
  Removed = 4

class Column(Enum):
  def __str__(self): return str(self.name)
  AppId = 0
  Name = 1
  State = 2
  DemoId = 3

NO_FILTER = '(any)'

wishlist_appids = []
data, data_sorted, data_sorted_filtered = {}, [], []

layout = [
  [sg.Text('Steam profile ID:'), sg.Input('', key='SteamProfileId', size=(20,1)), sg.Text('Country code:'), sg.Input('', key='SteamCountryCode', size=(3,1))],
  [sg.Text('Request:'), sg.Button('Wishlist'), sg.Button('Known demos', disabled=True), sg.Button('New demos', disabled=True), sg.Button('All demos', disabled=True),
    sg.ProgressBar(key='Progress', orientation='h', s=(10,20), expand_x=True, relief=sg.RELIEF_SUNKEN, max_value=100, visible=False),
    sg.Button('Stop', visible=False),],
  [sg.Text('Status:'), sg.Text('', key='ProgressText')],
  [sg.Text('Selection:'),
    sg.Text('(None)', key='Selection', size=(40,1), relief=sg.RELIEF_SUNKEN),
    sg.Button('Refresh', disabled=True),
    sg.Button('Visit page', disabled=True),
    sg.Button('Install/Play demo', disabled=True)],
  [sg.Text('Modify the State of selected line(s):'),
    sg.Button(State.Available, disabled=True),
    sg.Button(State.Installed, disabled=True),
    sg.Button(State.Tried, disabled=True),
    sg.Button(State.Missing, disabled=True),
    sg.Button(State.Removed, disabled=True)],
  [sg.Text('Filters:'),
    sg.Text('State ='), sg.Combo(key='FilterState', values=[NO_FILTER, State.Available, State.Installed, State.Tried, State.Missing, State.Removed], default_value=NO_FILTER, readonly=True, enable_events=True),
    sg.Text('Has a DemoId ='), sg.Combo(key='FilterDemo', values=[NO_FILTER, 'Yes', 'No'], default_value=NO_FILTER, readonly=True, enable_events=True),
    sg.Button('Clear all filters')],
  [sg.Text('', key='TableTitle')],
  [sg.Table(key='Table',
            values=data_sorted_filtered,
            headings=[Column.AppId, Column.Name, Column.State, Column.DemoId],
            col_widths=[10, 40, 10, 10],
            num_rows=10, justification='left', def_col_width=10, auto_size_columns=False, expand_x=True, expand_y=True, change_submits=True)],
]

#sg.theme('Dark Blue 3')
window = sg.Window('Demos in Steam wishlist', layout, resizable=True, finalize=True)
window.set_min_size((640, 768))
window.refresh()
window.move_to_center()
#window.maximize()

#================================================================================

def check_filters(item):
  filterState = window['FilterState'].get()
  if filterState != NO_FILTER:
    if item[Column.State.value] != filterState:
      return False
  filterDemo = window['FilterDemo'].get()
  if filterDemo != NO_FILTER:
    if filterDemo == 'Yes' and not item[Column.DemoId.value]:
      return False
    if filterDemo == 'No' and item[Column.DemoId.value]:
      return False
  return True

#================================================================================

def update_table():
  global wishlist_appids, data_sorted, data_sorted_filtered

  data_sorted = sorted(data.values(), key=lambda x: x[Column.Name.value].casefold())
  num_sorted = len(data_sorted)

  data_sorted_filtered = [x for x in data_sorted if check_filters(x)]
  num_filtered = len(data_sorted_filtered)

  if num_filtered != num_sorted:
    num_demos_str = f"{num_filtered} (of {num_sorted})"
  else:
    num_demos_str = f"{num_filtered}"

  window['TableTitle'].update(f"Listing {num_demos_str} demos, from a total of {len(wishlist_appids)} wishlist items:")

  colored_rows = []
  for i, v in enumerate(data_sorted_filtered):
      app_id = v[Column.AppId.value]
      state = v[Column.State.value]
      demo_id = v[Column.DemoId.value]
      if state == State.Removed:
        colored_rows += [(i, 'white', 'black')]
      elif not app_id in wishlist_appids:
        colored_rows += [(i, 'white', 'red')]
      elif state == State.Available and not demo_id:
        colored_rows += [(i, 'black', 'orange')]
      elif state == State.Available:
        colored_rows += [(i, 'white', 'green')]
      elif state == State.Installed and not demo_id:
        colored_rows += [(i, 'black', 'yellow')]
      elif state == State.Tried and not demo_id:
        colored_rows += [(i, 'black', 'yellow')]
      elif state == State.Missing:
        colored_rows += [(i, 'white', 'gray')]
      else:
        colored_rows += [(i, 'black', 'white')]

  window['Table'].update(data_sorted_filtered, row_colors=colored_rows)

#================================================================================

data_file = 'demos_installed.txt'
backup_file = 'demos_installed-backup.txt'

def load_data():
  global data
  print("Loading installed demos...")
  with open(data_file, 'r', encoding="utf-8") as file:
    lines = [line.rstrip() for line in file]
  if lines[0].startswith("steam_profile_id:"):
    _, steam_profile_id, steam_country_code = lines[0].split(':', 2)
    window['SteamProfileId'].update(steam_profile_id)
    window['SteamCountryCode'].update(steam_country_code)
  for line in lines[1:]:
    app_id_str, demo_id_str, prefix, name = line.split(':', 3)
    state = None
    if prefix == 'A': state = State.Available
    elif prefix == 'I': state = State.Installed
    elif prefix == 'T': state = State.Tried
    elif prefix == 'M': state = State.Missing
    if state:
      app_id = int(app_id_str)
      demo_id = int(demo_id_str) if demo_id_str != 'None' else None
      data[app_id] = [app_id, name, state, demo_id]
  update_table()

def save_data():
  global data_sorted
  print("Copying earlier installed demos to backup file...")
  shutil.copyfile(data_file, backup_file)
  print("Saving installed demos...")
  with open(data_file, 'w', encoding="utf-8") as file:
    steam_profile_id = window['SteamProfileId'].get()
    steam_country_code = window['SteamCountryCode'].get()
    file.write(f"steam_profile_id:{steam_profile_id}:{steam_country_code}\n")
    for v in data_sorted:
      state = v[Column.State.value]
      prefix = None
      if state == State.Available: prefix = 'A'
      elif state == State.Installed: prefix = 'I'
      elif state == State.Tried: prefix = 'T'
      elif state == State.Missing: prefix = 'M'
      if prefix:
        name = v[Column.Name.value]
        app_id = v[Column.AppId.value]
        demo_id = v[Column.DemoId.value]
        file.write(f"{app_id}:{demo_id}:{prefix}:{name}\n")

#================================================================================

def get_wishlist(steam_profile_id):
  global wishlist_appids

  #response_items = steam.users.get_profile_wishlist(steam_profile_id)
  response = requests.get(f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/", params={"steamid": steam_profile_id})
  response_items = response.json()['response']['items']

  wishlist_appids = [int(item['appid']) for item in response_items]
  print(f"Got {len(wishlist_appids)} apps for profile {steam_profile_id}")
  update_table()

def request_wishlist():
  steam_profile_id = window['SteamProfileId'].get()
  if steam_profile_id and steam_profile_id.isnumeric():
    print("Requesting wishlist...")
    window['ProgressText'].update(f"Requesting wishlist...")
    window.refresh()
    try:
      get_wishlist(steam_profile_id)
      window['ProgressText'].update(f"Wishlist request completed!")
    except Exception as e:
      print(e)
      window['ProgressText'].update(f"Exception ({type(e)}) occurred!")
    window['Known demos'].update(disabled=(not wishlist_appids))
    window['New demos'].update(disabled=(not wishlist_appids))
    window['All demos'].update(disabled=(not wishlist_appids))

#================================================================================

batch_size, limit_secs = 200, 300 # Steam rate-limiting
request_interval_secs = limit_secs / batch_size
avg_request_secs = 1.75 # Empirical value, modify if needed!
retry_delay_secs = 10

def get_app_details(app_id, country_code):
  global data

  #details = steam.apps.get_app_details(app_id=app_id, country="SE", filters="basic,demos")
  response = requests.get(
    f"https://store.steampowered.com/api/appdetails",
    params={
       "appids": app_id,
       "cc": country_code,
       "filters": "basic,demos"
    }
  )

  if response.ok:
    #print(response.json())
    details = response.json()[str(app_id)]['data']
    name = details.get('name')
    demos = details.get('demos')
    demo_appid_str = None
    if demos:
      demo_appid_str = ",".join([str(demo.get('appid')) for demo in demos if demo.get('appid')])
    if demo_appid_str and ("," in demo_appid_str):
      print(f"Warning: multiple demo-ids for app '{name}': {demo_appid_str}")
    demo_id = int(demo_appid_str) if demo_appid_str else None
    row = data.get(app_id)
    if row:
      row[Column.Name.value] = name
      if row[Column.DemoId.value] != demo_id:
        print(f"Updating demo-id for app: '{name}'")
        row[Column.DemoId.value] = demo_id
        update_table()
    elif demo_id:
      data[app_id] = [app_id, name, State.Available, demo_id]
      print(f"Found new app with demo: '{name}'")
      update_table()
    #print(f"{name} --> {demo_appid}")
    return True
  # Failure:
  print(f"App-details request failed, response status code: {response.status_code}")
  # 200 = successful
  # 429 = too many requests (resend in 10 secs intervals until successful?)
  # 403 = forbidden (wait 5 minutes before resending?)
  # 502 = bad gateway
  #print(response.headers)
  #print(response.text)
  #print(response.content)
  return False

#================================================================================

load_data()

request_wishlist()

# Loop to process "events" and get the "values" of the inputs
while True:
  event, values = window.read()
  #print(f'Event {event} - Values: {values}')

  if event == sg.WIN_CLOSED:
    window.timer_stop_all()
    break

  if event == 'Wishlist':
    request_wishlist()

  if event == 'Known demos' or event == 'New demos' or event == 'All demos':
    window['Progress'].update(visible=True)
    window['Stop'].update(visible=True)
    if event == 'Known demos':
      fetch_appids = [id for id in wishlist_appids if id in data.keys()]
    elif event == 'New demos':
      fetch_appids = [id for id in wishlist_appids if not id in data.keys()]
    elif event == 'All demos':
      fetch_appids = [id for id in wishlist_appids]
    country_code = values['SteamCountryCode']
    print(f"Starting requests for app-details on '{event}' ({len(fetch_appids)} IDs, cc = '{country_code}')...")
    print(f"(Request interval: {request_interval_secs} secs)")
    curr_app_idx = 0
    start_time = time.time()
    window.timer_start(0, repeating=False) # milliseconds

  if event == sg.EVENT_TIMER:
    if curr_app_idx < len(fetch_appids):
      app_id = fetch_appids[curr_app_idx]
      #print(f"Requesting app-details for appid: {app_id}")
      remain_secs = avg_request_secs * (len(fetch_appids) - curr_app_idx - 1)
      m, s = int(remain_secs / 60), int(remain_secs) % 60
      window['ProgressText'].update(f"Requesting demo for game {curr_app_idx+1}/{len(fetch_appids)}, time remaining: {m}m {s}s")
      window.refresh()
      try:
        if get_app_details(app_id, country_code):
          window['Progress'].update(current_count=curr_app_idx+1, max=len(fetch_appids))
          curr_app_idx += 1
          if curr_app_idx < len(fetch_appids):
            window.timer_start(1000 * request_interval_secs, repeating=False) # milliseconds
          else:
            window.timer_start(0, repeating=False) # milliseconds
        else:
          # FIXME - allow failing on "too many requests", implement exponential back-off?
          print(f"Rate-limited, retrying after a delay of {retry_delay_secs} secs...")
          window['ProgressText'].update(f"Rate-limited, waiting {retry_delay_secs} secs!")
          window.timer_start(1000 * retry_delay_secs, repeating=False) # milliseconds
      except Exception as e:
        print(e)
        window['ProgressText'].update(f"Exception ({type(e)}) occurred, retrying in {retry_delay_secs} secs!")
        window.timer_start(1000 * retry_delay_secs, repeating=False) # milliseconds
    else:
      print("App-details requests completed.")
      elapsed_secs = time.time() - start_time
      m, s = int(elapsed_secs / 60), int(elapsed_secs) % 60
      avg_secs = "{:.2f}".format(elapsed_secs / len(fetch_appids))
      window['ProgressText'].update(f"Demo requests completed! (Time elapsed: {m}m {s}s, avg {avg_secs} secs)")
      window['Progress'].update(visible=False)
      window['Stop'].update(visible=False)
      update_table()
      if len(fetch_appids) == 1:
        selected_rows = [i for i, v in enumerate(data_sorted_filtered) if v[Column.AppId.value] == fetch_appids[0]]
        window['Table'].update(select_rows=selected_rows)

  if event == 'Stop':
    if curr_app_idx < len(fetch_appids):
      window.timer_stop_all()
      print("App-details requests stopped before completion!")
      # FIXME - display elapsed time?
      window['ProgressText'].update(f"Demo requests were stopped!")
      window['Progress'].update(visible=False)
      window['Stop'].update(visible=False)
      update_table()

  if event == 'FilterState' or event == 'FilterDemo':
    update_table()

  if event == 'Clear all filters':
    window['FilterState'].update(NO_FILTER)
    window['FilterDemo'].update(NO_FILTER)
    update_table()

  selected_rows = values['Table']

  if event == 'Table':
    if len(selected_rows) == 0:
      window['Selection'].update("(None)")
      window['Refresh'].update(disabled=True)
      window['Visit page'].update(disabled=True)
      window['Install/Play demo'].update(disabled=True)
      for state in State: window[state.name].update(disabled=True)
    elif len(selected_rows) == 1:
      idx = selected_rows[0]
      app_name = data_sorted_filtered[idx][Column.Name.value]
      window['Selection'].update(app_name)
      demo_id = data_sorted_filtered[idx][Column.DemoId.value]
      window['Refresh'].update(disabled=False)
      window['Visit page'].update(disabled=False)
      window['Install/Play demo'].update(disabled=(not demo_id))
      for state in State: window[state.name].update(disabled=False)
    else: # Multi-selection
      window['Selection'].update("(Multiple)")
      window['Refresh'].update(disabled=True)
      window['Visit page'].update(disabled=True)
      window['Install/Play demo'].update(disabled=True)
      for state in State: window[state.name].update(disabled=False)

  if selected_rows:
    needs_refresh = False
    if event in [state.name for state in State]:
      for idx in selected_rows:
        data_sorted_filtered[idx][Column.State.value] = event
      needs_refresh = True
    if needs_refresh:
      update_table()
      if values['FilterState'] == NO_FILTER and values['FilterDemo'] == NO_FILTER:
        window['Table'].update(select_rows=selected_rows)
  
  if len(selected_rows) == 1:
    idx = selected_rows[0]
    if event == 'Refresh':
      app_id = data_sorted_filtered[idx][Column.AppId.value]
      fetch_appids = [app_id]
      country_code = values['SteamCountryCode']
      print(f"Starting request for app-details on appid {app_id} (cc = '{country_code}')...")
      curr_app_idx = 0
      start_time = time.time()
      window.timer_start(0, repeating=False) # milliseconds
    if event == 'Visit page':
      app_id = data_sorted_filtered[idx][Column.AppId.value]
      webbrowser.open(f"https://store.steampowered.com/app/{app_id}/")
    if event == 'Install/Play demo':
      demo_id = data_sorted_filtered[idx][Column.DemoId.value]
      if demo_id:
        webbrowser.open(f"steam://rungameid/{demo_id}")

save_data()

window.close()
