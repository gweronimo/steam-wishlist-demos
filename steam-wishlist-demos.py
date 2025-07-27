import time
from enum import Enum
import os.path
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
  Wished = 0
  Installed = 1
  Tried = 2
  Failed = 3

class Column(Enum):
  def __str__(self): return str(self.name)
  AppID = 0
  Name = 1
  State = 2
  DemoID = 3

NO_FILTER = '(any)'

wishlist_appids = []
data, data_sorted, data_sorted_filtered = {}, [], []

layout = [
  [sg.Text('Steam profile ID:'), sg.Input('', key='SteamProfileId', size=(20,1)), sg.Text('Country code:'), sg.Input('', key='SteamCountryCode', size=(3,1))],
  [sg.Text('Request:'), sg.Button('Wishlist'), sg.Button('App-details', disabled=True),
    sg.ProgressBar(key='Progress', orientation='h', s=(10,20), expand_x=True, relief=sg.RELIEF_SUNKEN, max_value=100, visible=False),
    sg.Button('Stop', visible=False),],
  [sg.Text('Status:'), sg.Text('', key='ProgressText')],
  [sg.Text('Selection:'),
    sg.Text('(None)', key='Selection', size=(40,1), relief=sg.RELIEF_SUNKEN),
    sg.Button('Refresh', disabled=True),
    sg.Button('Visit page', disabled=True),
    sg.Button('Install/Play demo', disabled=True)],
  [sg.Text('Modify the State of selected line(s):'),
    sg.Button(State.Wished, disabled=True),
    sg.Button(State.Installed, disabled=True),
    sg.Button(State.Tried, disabled=True),
    sg.Button(State.Failed, disabled=True)],
  [sg.Text('Filters:'),
    sg.Text('State ='), sg.Combo(key='FilterState', values=[NO_FILTER, State.Wished, State.Installed, State.Tried, State.Failed], default_value=NO_FILTER, readonly=True, enable_events=True),
    sg.Text('Has a DemoID ='), sg.Combo(key='FilterDemo', values=[NO_FILTER, 'Yes', 'No'], default_value=NO_FILTER, readonly=True, enable_events=True),
    sg.Button('Reset')],
  [sg.Text('', key='TableTitle')],
  [sg.Table(key='Table',
            values=data_sorted_filtered,
            headings=[Column.AppID, Column.Name, Column.State, Column.DemoID],
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
    if filterDemo == 'Yes' and not item[Column.DemoID.value]:
      return False
    if filterDemo == 'No' and item[Column.DemoID.value]:
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
    num_items_str = f"{num_filtered} (of {num_sorted})"
  else:
    num_items_str = f"{num_filtered}"
  window['TableTitle'].update(f"Listing {num_items_str} wishlist items:")

  colored_rows = []
  for i, v in enumerate(data_sorted_filtered):
      app_id = v[Column.AppID.value]
      state = v[Column.State.value]
      demo_id = v[Column.DemoID.value]
      if not app_id in wishlist_appids:
        colored_rows += [(i, 'white', 'red')]
      elif state == State.Wished and not demo_id:
        colored_rows += [(i, 'black', 'orange')]
      elif state == State.Wished:
        colored_rows += [(i, 'white', 'green')]
      elif state == State.Installed and not demo_id:
        colored_rows += [(i, 'black', 'yellow')]
      elif state == State.Tried and not demo_id:
        colored_rows += [(i, 'black', 'yellow')]
      elif state == State.Failed:
        colored_rows += [(i, 'white', 'gray')]
      else:
        colored_rows += [(i, 'black', 'white')]

  window['Table'].update(data_sorted_filtered, row_colors=colored_rows)

#================================================================================

data_file = 'demos_installed.txt'
backup_file = 'demos_installed-backup.txt'

def load_data():
  global data

  if not os.path.isfile(data_file):
    return
  
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
    if prefix == 'W': state = State.Wished
    elif prefix == 'I': state = State.Installed
    elif prefix == 'T': state = State.Tried
    elif prefix == 'F': state = State.Failed
    if state:
      app_id = int(app_id_str)
      demo_id = int(demo_id_str) if demo_id_str != 'None' else None
      data[app_id] = [app_id, name, state, demo_id]

  update_table()

#--------------------------------------------------------------------------------

def save_data():
  global data_sorted

  if os.path.isfile(data_file):
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
      if state == State.Wished: prefix = 'W'
      elif state == State.Installed: prefix = 'I'
      elif state == State.Tried: prefix = 'T'
      elif state == State.Failed: prefix = 'F'
      if prefix:
        name = v[Column.Name.value]
        app_id = v[Column.AppID.value]
        demo_id = v[Column.DemoID.value]
        file.write(f"{app_id}:{demo_id}:{prefix}:{name}\n")

#================================================================================

def get_wishlist(steam_profile_id):
  global wishlist_appids

  #response_items = steam.users.get_profile_wishlist(steam_profile_id)
  response = requests.get(f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/", params={"steamid": steam_profile_id})

  if not response.ok:
    return False
  
  response_items = response.json()['response']['items']

  wishlist_appids = [int(item['appid']) for item in response_items]
  print(f"Got {len(wishlist_appids)} apps for profile {steam_profile_id}")

  for app_id in wishlist_appids:
    row = data.get(app_id)
    if not row:
      data[app_id] = [app_id, "<Name is not fetched yet>", State.Wished, None]

  update_table()

  missing_apps = [app_id for app_id in data.keys() if not app_id in wishlist_appids]
  if len(missing_apps) > 0:
    reply = sg.popup_yes_no(
      f"Found {len(missing_apps)} AppIDs no longer on the wishlist.\nShould they be removed?\n(If not, they will just be marked in red.)",
      title="Remove items?")
    if reply == "Yes":
      for app_id in missing_apps:
        data.pop(app_id)
      update_table()

  return True

#--------------------------------------------------------------------------------

def request_wishlist():
  steam_profile_id = window['SteamProfileId'].get()
  if not steam_profile_id:
    window['ProgressText'].update(f"Enter a Steam profile ID first!", text_color='red')
  elif not steam_profile_id.isnumeric():
    window['ProgressText'].update(f"Steam profile ID must consist of only digits!", text_color='red')
  else:
    print("Requesting wishlist...")
    window['ProgressText'].update(f"Requesting wishlist...", text_color='white')
    window.refresh()
    try:
      if get_wishlist(steam_profile_id):
        window['ProgressText'].update(f"Wishlist request completed!", text_color='white')
      else:
        window['ProgressText'].update(f"Failed to request wishlist!", text_color='red')
    except Exception as e:
      e_type = type(e).__name__
      print(f"{e_type} '{e}'")
      window['ProgressText'].update(f"{e_type} '{e}'", text_color='red')
    window['App-details'].update(disabled=(not wishlist_appids))

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

    demo_id = None
    if demos:
      demo_ids = [demo.get('appid') for demo in demos if demo.get('appid')]
      if len(demo_ids) > 0:
        demo_id = demo_ids[0]
      if len(demo_ids) > 1:
        print(f"Warning: multiple demo-ids for app '{name}': {demo_ids}")

    needs_update = False
    row = data.get(app_id)
    if row:
      if row[Column.Name.value] != name:
        row[Column.Name.value] = name
        print(f"Updated app Name: '{name}'")
        needs_update = True
      if row[Column.DemoID.value] != demo_id:
        row[Column.DemoID.value] = demo_id
        print(f"Updated demo-ID for app: '{name}'")
        needs_update = True
    if needs_update:
      update_table()
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

  if event == 'App-details':
    fetch_appids = [id for id in wishlist_appids]
    window['Progress'].update(visible=True)
    window['Stop'].update(visible=True)
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
      window['ProgressText'].update(f"Requesting app-details for item {curr_app_idx+1}/{len(fetch_appids)}, time remaining: {m}m {s}s", text_color='white')
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
          window['ProgressText'].update(f"Rate-limited, waiting {retry_delay_secs} secs!", text_color='orange')
          window.timer_start(1000 * retry_delay_secs, repeating=False) # milliseconds
      except Exception as e:
        e_type = type(e).__name__
        print(f"{e_type} '{e}'")
        window['ProgressText'].update(f"{e_type} '{e}' - retrying in {retry_delay_secs} secs!", text_color='red')
        window.timer_start(1000 * retry_delay_secs, repeating=False) # milliseconds
    else:
      print("App-details requests completed.")
      elapsed_secs = time.time() - start_time
      m, s = int(elapsed_secs / 60), int(elapsed_secs) % 60
      avg_secs = "{:.2f}".format(elapsed_secs / len(fetch_appids))
      window['ProgressText'].update(f"App-detail requests completed! (Time elapsed: {m}m {s}s, avg {avg_secs} secs)", text_color='white')
      window['Progress'].update(visible=False)
      window['Stop'].update(visible=False)
      update_table()
      if len(fetch_appids) == 1:
        selected_rows = [i for i, v in enumerate(data_sorted_filtered) if v[Column.AppID.value] == fetch_appids[0]]
        window['Table'].update(select_rows=selected_rows)

  if event == 'Stop':
    if curr_app_idx < len(fetch_appids):
      window.timer_stop_all()
      print("App-details requests stopped before completion!")
      # FIXME - display elapsed time?
      window['ProgressText'].update(f"Demo requests were stopped!", text_color='white')
      window['Progress'].update(visible=False)
      window['Stop'].update(visible=False)
      update_table()

  if event == 'FilterState' or event == 'FilterDemo':
    update_table()

  if event == 'Reset':
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
      demo_id = data_sorted_filtered[idx][Column.DemoID.value]
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
    for state in State:
      if event == state.name:
        for idx in selected_rows:
          app_id = data_sorted_filtered[idx][Column.AppID.value]
          row = data.get(app_id)
          if row:
            row[Column.State.value] = state
        needs_refresh = True
        break
    if needs_refresh:
      update_table()
      if values['FilterState'] == NO_FILTER and values['FilterDemo'] == NO_FILTER:
        window['Table'].update(select_rows=selected_rows)
  
  if len(selected_rows) == 1:
    idx = selected_rows[0]
    if event == 'Refresh':
      app_id = data_sorted_filtered[idx][Column.AppID.value]
      fetch_appids = [app_id]
      country_code = values['SteamCountryCode']
      print(f"Starting request for app-details on appid {app_id} (cc = '{country_code}')...")
      curr_app_idx = 0
      start_time = time.time()
      window.timer_start(0, repeating=False) # milliseconds
    if event == 'Visit page':
      app_id = data_sorted_filtered[idx][Column.AppID.value]
      webbrowser.open(f"https://store.steampowered.com/app/{app_id}/")
    if event == 'Install/Play demo':
      demo_id = data_sorted_filtered[idx][Column.DemoID.value]
      if demo_id:
        webbrowser.open(f"steam://rungameid/{demo_id}")

save_data()

window.close()
