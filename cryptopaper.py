#!/usr/bin/env python3
## (c) 2021-2023  Kerry Fraser-Robinson
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame, asyncio, aiohttp, json, threading
from aiohttp import ClientTimeout
import datetime, time, math, socket, urllib, string, io, sys, subprocess
from bs4 import BeautifulSoup
 
os.chdir(os.path.dirname(os.path.abspath(__file__)))
LIBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
TITLE, VERSION = 'Cryptopaper', 'v1.1.1'

WIN_W, WIN_H, CHART_TOP, CHART_BOTTOM = 2200, 1650, 450, 1450
CHART_HEIGHT = CHART_BOTTOM - CHART_TOP
CHART_COL_W, MAX_CANDLES, SECS_PER_CANDLE =  16, 720, 30
NL, MIN_CONTRAST, BLACK, white = "\n", 155, (0, 0, 0), (255, 255, 255) # white can be adjusted for contrast
VI_RADIUS, VI_RATIO = 100.0, 10 # Volatility indicator
VI_CENTER = WIN_W // 2, WIN_H - VI_RADIUS 
T_START, TIMEOUT, FPS = int(time.time()) // 60, 1.0, 30
candles, news, font_cache, ip_addr, weather, btc_usd_spot, ltc_btc_rate = [], [], {}, '', '', 0, 0

BADGE = pygame.image.load(os.path.join(LIBDIR,'tryzub-100.png'))
FONT_PATH = os.path.join(LIBDIR,"Code New Roman.otf")

WAR_DAYS, WAR_KIT = 40, ['tank', 'apv', 'arty', 'mlrs', 'aa', 'jet', 'helo', 'drone', 'missile', 'truck']
KEY_MAP = {'APC': 'apv', 'field artillery': 'arty', 'MRL': 'mlrs', 'anti-aircraft warfare': 'aa', 'aircraft': 'jet', 'helicopter': 'helo', 'cruise missiles': 'missile', 'vehicles and fuel tanks': 'truck'}
war_today_change, war_today_stats, orc_figures, war_day = [], [], [], 0

last_update_day, last_update_hour = datetime.date.today(), 0

BTC_INTERVAL, LTC_INTERVAL = 30, 60

try:
    RESCALE_RESOLUTION = (int(sys.argv[1]), (int(sys.argv[1]) // 4) * 3)
    if RESCALE_RESOLUTION[0] < 800: RESCALE_RESOLUTION = (800, 600) # WS-103 has width 1872 
except: RESCALE_RESOLUTION = (WIN_W, WIN_H)

pygame.init()
rendered_display = pygame.display.set_mode( RESCALE_RESOLUTION, pygame.NOFRAME | pygame.DOUBLEBUF | pygame.HWSURFACE, 8 )
pygame.display.set_caption(TITLE + ' ' + VERSION)
pygame.mouse.set_visible(False)
clock = pygame.time.Clock()
display = pygame.Surface((WIN_W, WIN_H))

# Async functions
def cancel_tasks_and_stop_loop(loop, tasks):
    for task in tasks:
        task.cancel()
    loop.call_soon_threadsafe(loop.stop)

async def get_btc_spot(timeout=TIMEOUT):
    global btc_usd_spot
    try:
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=timeout)) as session:
            async with session.get("https://www.bitstamp.net/api/v2/ticker/btcusd") as response:
                data = await response.json()
                return float(data['last'])
    except:
        notice('BTC TIMEOUT', f"Using {str(btc_usd_spot)}")
        return btc_usd_spot

async def get_ltc_btc_rate(timeout=TIMEOUT):
    global ltc_btc_rate
    try:
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=timeout)) as session:
            async with session.get("https://www.bitstamp.net/api/v2/ticker/ltcbtc") as response:
                data = await response.json()
                return float(data['last'])
    except:
        notice('LTC TIMEOUT', f"Using {ltc_btc_rate}")
        return ltc_btc_rate

async def update_btc_usd_spot(interval, stop_event):
    global btc_usd_spot
    while not stop_event.is_set():
        try:
            btc_usd_spot = await asyncio.wait_for(get_btc_spot(), timeout=interval)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            notice('Error', e)
        await asyncio.sleep(interval)

async def update_ltc_btc_rate(interval, stop_event):
    global ltc_btc_rate
    while not stop_event.is_set():
        try:
            ltc_btc_rate = await asyncio.wait_for(get_ltc_btc_rate(), timeout=interval)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            notice('Error', e)
        await asyncio.sleep(interval)

def run_asyncio_loop(loop, stop_event, btc_interval, ltc_interval, shared_data):
    asyncio.set_event_loop(loop)
    btc_update_task = loop.create_task(update_btc_usd_spot(btc_interval, stop_event))
    ltc_update_task = loop.create_task(update_ltc_btc_rate(ltc_interval, stop_event))
    shared_data['tasks'].extend([btc_update_task, ltc_update_task])
    loop.run_forever()
    loop.close()

# Function to stop the asyncio loop from another thread
def stop_asyncio_loop(loop): loop.call_soon_threadsafe(loop.stop)

# Blocking functions
def fetch_orc_stats(numDays = 40, timeout = TIMEOUT):

    def calc_today_losses(dict_list):
        result = {}
        for d in dict_list:
            for k, v in d.items():
                if isinstance(v, (int, float)):
                    result[k] = {'min': min(result.get(k, {}).get('min', v), v), 'max': max(result.get(k, {}).get('max', v), v)}
        return [{k: v['max'] - v['min'] for k, v in result.items()}]

    def rename_keys(dict_list): return [{KEY_MAP.get(key, key): value for key, value in d.items()} for d in dict_list]

    def fetch_orc_equipment(timeout = TIMEOUT):
        global war_day, war_today_stats, war_today_change
        with urllib.request.urlopen("https://raw.githubusercontent.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset/main/data/russia_losses_equipment.json", timeout=60) as url:
            js = json.loads(url.read())
        war_day = js[-1]['day']
        war_today_stats = rename_keys([js[-1]])
        war_today_change = rename_keys(calc_today_losses(js[-2:]))
        return

    tally, daily = [], []
    with urllib.request.urlopen("https://raw.githubusercontent.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset/main/data/russia_losses_personnel.json", timeout=60) as url:
        dict = json.loads(url.read())
        for i in range(1, numDays + 2):
            tally.insert(0, dict[0-i]['personnel'])
    daily = [int(tally[i+1]) - int(tally[i]) for i in range(len(tally)-1)]
    fetch_orc_equipment()
    
    return(daily)
    
def fetch_weather(timeout = TIMEOUT):
    wttr_url = f"https://wttr.in/{(LOCATION.replace(' ','_'))}?0FQAT"
    try:
        with urllib.request.urlopen(wttr_url, timeout=60) as url:
            data = url.read()
    except:
        notice('WTTR TIMEOUT', f'Using: {NL + weather}') 
        return weather
    result = data.decode()
    if '°' not in result: 
        notice('WTTR EMPTY', f'Using: {NL + weather}') 
        return weather
    result = result.replace('\u2196','\u02f9').replace('\u2197','\u02fa').replace('\u2198','\u02fc').replace('\u2199','\u02fb') # Font shortcomings
    return result + ' ' * 16 + f'({datetime.datetime.now().strftime("%H:%M")})'

def fetch_bbc_news(headline_count=4, timeout=TIMEOUT):
    # Return headline_count headline strings from BBC news
    results = []
    try:
        with urllib.request.urlopen("https://www.bbc.com/news/world", timeout=timeout) as url:
            data = url.read()
    except:
        return(['', '', '  No headlines found'])
    soup = BeautifulSoup(data, 'html.parser')
    headlines = soup.find('body').find_all('h3')

    for i in range(len(headlines)):
        if headlines[i].text.strip() not in results: results.append(f'{headlines[i].text.strip()}')
        if len(results) >= headline_count: break

    return results

def get_btc_spot_once(timeout=TIMEOUT):
    global btc_usd_spot
    try:
        with urllib.request.urlopen("https://www.bitstamp.net/api/v2/ticker/btcusd", timeout=timeout) as url:
            data = json.loads(url.read())
            return(float(data['last']))
    except:
        notice('BTC TIMEOUT', f"Using {str(btc_usd_spot)}")
        return(btc_usd_spot)

def print_at(canvas, text_x: int, text_y: int, text_string: str, font_size: int = 16, inverse: bool = False, align: int = 0):
    global font_cache
    font_key = (FONT_PATH, font_size)
    font_cache.setdefault(font_key, pygame.font.Font(FONT_PATH, font_size))
    font = font_cache[font_key]

    text_style, rect_style = (white, BLACK) if inverse else (BLACK, white)
    
    lines = text_string.split(NL)
    y_offset = 0
    for line in lines:
        text = font.render(str(line), True, text_style, rect_style)
        text_rect = text.get_rect()

        if align == 1: # Center
            text_rect.topleft = ((WIN_W // 2) - (text_rect.width // 2), text_y + y_offset)
        elif align == 2: # Right
            text_rect.topleft = (WIN_W - text_rect.width, text_y + y_offset)
        else: # Left (default)
            text_rect.topleft = (text_x, text_y + y_offset)

        canvas.blit(text, text_rect)

        y_offset += font.get_height()  # Increment Y offset by the font height for the next line

def ip_address():
    try:
        ip = ((([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [[(s.connect(
            ("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["(No IP)"])[0])
    except:
        ip = "(IP Timeout)"
    return ip

def unix_minute(): return (int(time.time())//60) - T_START

def coords_from_angle(radius, angle):
    # Calculate x,y coords for a point 'radius' distance from the origin along a path given by 'angle'
    angle_rad = math.radians(180 - angle)
    return radius * math.sin(angle_rad), radius * math.cos(angle_rad)

def fraction_of_range(value, min_val, max_val, rate=100):
    if max_val <= min_val: return rate
    value = min(max_val, max(min_val, value))
    return int(((value - min_val) / (max_val - min_val)) * rate)

def dhm(seconds):
    days, hrs, mins = seconds // 86400, (seconds // 3600) % 24, (seconds // 60) % 60
    return f"{hrs}h{mins:02}m" if days < 1 else f"{days}d{hrs:02}h{mins:02}m" 

def ord_strftime(fmt, date_obj):
    ordinal_suffix = lambda n: "th" if 4 <= abs(n) % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(abs(n) % 10, "th")
    return date_obj.strftime(fmt).replace('{S}', str(date_obj.day) + ordinal_suffix(date_obj.day))

def display_image(canvas, image, x, y, rescale_factor: float = 1.0):
    if rescale_factor != 1.0:
        scaled_width = int(image.get_width() * rescale_factor)
        scaled_height = int(image.get_height() * rescale_factor)
        image = pygame.transform.scale(image, (scaled_width, scaled_height))
    canvas.blit(image, image.get_rect().move(x, y))

def draw_chart(canvas, left_x, top_y, data_list, col_width = 16):
    width = col_width * len(data_list) + 6
    height = 100
    box = pygame.Rect(left_x, top_y, width, height)
    pygame.draw.rect(canvas, (0, 0, 0), box, 3)
    top_gap = max(data_list) // 10
    for i in range(0, len(data_list)):
        y = fraction_of_range(data_list[i], 0, max(data_list)+top_gap, height)
        pygame.draw.line(canvas, (0, 0, 0), (2+left_x + (i * col_width) + col_width//2,
                         top_y+height-2), (2+left_x + (i * col_width) + col_width//2, top_y+height-y), col_width-2)

def notice(type: str = 'STATUS', content: str = ''): print(f"[{datetime.datetime.now().strftime('%b-%d %H:%M')}] {type}:  {content}")

def draw_equipment_losses(canvas, x, y, scale: float = 0.18):
    offset = 0
    for icon in WAR_KIT:
        classification = icon
        icon = pygame.image.load(os.path.join(LIBDIR,f'{icon}.png'))
        display_image(canvas, icon, x + offset, y + 28, scale)
        offset += int(450 * scale) + 4
        print_at(canvas, (offset + 20) - int(450 * scale) + 32, y + 6, f"{war_today_change[0][classification]}", 24)
    pygame.draw.rect(canvas, BLACK, pygame.Rect(x-4, y - 1, offset, 82), 3, 6)

def draw_main_chart():
    # Chart Frame
    pygame.draw.rect(display, 0, pygame.Rect( 3, CHART_TOP - 10, WIN_W - 6, CHART_HEIGHT + 10), 6, 3 )

    # Plot candles
    plot_w = WIN_W // MAX_CANDLES # 3px
    previous = CHART_HEIGHT - 1 # Bottom of chart
    for i in range(len(candles)):
        x = 8 + (i + 1 ) * plot_w
        y = CHART_TOP + ( CHART_HEIGHT - fraction_of_range(candles[i], min(candles), max(candles), CHART_HEIGHT - 8) ) - 9
        pygame.draw.circle(display, BLACK, (x, y), plot_w - 1, 0)
        # Draw a vertical line between jumps:
        if (abs(y - previous) >= plot_w) and i > 0 and y < CHART_BOTTOM:
            pygame.draw.line(display, BLACK, (x - plot_w + 1, previous - 1), (x - 1, y - 1), plot_w)
        # Draw vertical grid line every 120 candles
        if (i % 120 == 0) and i > 0: pygame.draw.line(display, BLACK, ( x + 6, CHART_TOP - 6 ), ( x + 6, CHART_BOTTOM - 1), 1 )

        previous = y

    # Draw horizontal marker for current price visibility
    pygame.draw.line(display, BLACK, (x, y - 1), (WIN_W - 8, y - 1), 1)

def draw_volatility_indicator():
    if (max(candles) - min(candles) <= 0): volatility = 0
    else: volatility = ((max(candles) - min(candles)) / max(candles)) * 100
    pygame.draw.circle(display, 0, VI_CENTER, VI_RADIUS, 5)
    pygame.draw.circle(display, 0, VI_CENTER, min(volatility * VI_RATIO, VI_RADIUS) )
    print_at(display, VI_CENTER[0] + VI_RADIUS - 16, CHART_BOTTOM + 4, f"${max(candles) - min(candles):,.0f}", 36)
    print_at(display, VI_CENTER[0] + VI_RADIUS - 12, WIN_H - 48, f"{volatility:,.2f}%", 48)

    # Movement Indicator Box
    MIB_H, MIB_W, MIB_BAR_H = 180, 48, 6
    MIB_X, MIB_Y = VI_CENTER[0] - 164, VI_CENTER[1] - (MIB_H // 2)
    pygame.draw.rect(display, 0, pygame.Rect(MIB_X, MIB_Y, MIB_W, MIB_H), 5, 0)
    value = fraction_of_range( btc_usd_spot, min(candles), max(candles), (MIB_H - 18) )
    pygame.draw.rect(display, 0, pygame.Rect(MIB_X + 8, MIB_Y + (MIB_H - value) - (MIB_BAR_H * 2), MIB_W - 16, MIB_BAR_H), 0)

    # Draw second hand for clock; white (not contrast-adaptive) if volatility indicator would otherwise obscure it.
    (start_x, start_y) = coords_from_angle( int(VI_RADIUS * 0.6), int(time.strftime('%S')) * 6 )
    (end_x, end_y) = coords_from_angle( int(VI_RADIUS * 1.0) - 8, int(time.strftime('%S')) * 6 )
    pygame.draw.line(display, BLACK if volatility < 7 else (255,255,255), ( VI_CENTER[0] + start_x, VI_CENTER[1] + start_y ), ( VI_CENTER[0] + end_x, VI_CENTER[1] + end_y ), 3)

def draw_war_stats():
    draw_chart(display, 16, CHART_BOTTOM + 94, orc_figures, CHART_COL_W)
    print_at(display, (WAR_DAYS * CHART_COL_W) + 34, CHART_BOTTOM + 118, f"{orc_figures[-1]}", 60)
    print_at(display, (WAR_DAYS * CHART_COL_W) + 36, CHART_BOTTOM + 98, f"High: {max(orc_figures)}", 16)
    print_at(display, (WAR_DAYS * CHART_COL_W) + 46, CHART_BOTTOM + 176, f"Low: {min(orc_figures)}", 16)
    print_at(display, (WAR_DAYS * CHART_COL_W) + 190, CHART_BOTTOM + 142, f"{war_day}", 48)
    print_at(display, (WAR_DAYS * CHART_COL_W) + 200, CHART_BOTTOM + 102, "Day", 36)
    draw_equipment_losses(display, 20, CHART_BOTTOM + 6)

# Pygame main loop
def pygame_loop(stop_event):
    global news, candles, orc_figures, white, last_update_day, last_update_hour, weather
    # Setup
    ps = int(time.time())-1
    previous_minute = 0
    previous_tick = (int(time.time()) // SECS_PER_CANDLE) - 1
    ip_addr = ip_address()
    running = True
    while running:
        if (ps == int(time.time())):
            clock.tick(FPS)
            continue
        else: ps = int(time.time())

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif (event.key == pygame.K_UP): # Contrast adjustments
                    if white[0] < 255:  white = ( white[0] + 20, white[0] + 20, white[0] + 20)
                elif (event.key == pygame.K_DOWN):
                    if white[0] > MIN_CONTRAST: white = ( white[0] - 20, white[0] - 20, white[0] - 20)

        display.fill(white)
        
        # Show weather
        print_at(display, 1176, CHART_BOTTOM + 38, weather, 22)

        # Show clock
        pygame.draw.rect(display, BLACK, pygame.Rect(0, 0, WIN_W, 12))
        print_at(display, 0, 12, time.strftime(' %H:%M '), 204, True)

        # Show status 
        print_at(display, WIN_W, CHART_BOTTOM + 9, f"{f'[{LOCATION}]' if any(char in string.digits for char in LOCATION) else LOCATION}   {ip_addr}  {(str((white[0] - MIN_CONTRAST) // 20) + '  ').replace('5 ','')}Up: {dhm(unix_minute() * 60)}  ", 24, False, 2)
        print_at(display, 1366, WIN_H - 16, VERSION, 16)

        # Show date
        today = datetime.date.today()
        print_at(display, WIN_W // 2, 22, today.strftime('%a') + ' ' + ord_strftime('{S}', today), 102, False, 1)
        print_at(display, WIN_W // 2, 122, today.strftime('%b \'%y'), 90, False, 1)
        pygame.draw.rect(display, BLACK, pygame.Rect(0, 215, WIN_W, 8))

        # Get spot price every candle
        this_tick = int(time.time()) // SECS_PER_CANDLE
        if this_tick > previous_tick:
            previous_tick = this_tick
            candles.append(btc_usd_spot)
            if len(candles) > MAX_CANDLES: del candles[0]

        this_hour = int(time.strftime('%H'))
        # Once per minute tasks:
        if (previous_minute != unix_minute()):
            previous_minute = unix_minute()
            news = fetch_bbc_news(4, 1.0)

            # New stats are usually posted around midday so should most likely be there by 14:05 
            if ( (last_update_day != today) and (datetime.datetime.now().time() > datetime.time(14, 5, 0)) ): 
                last_update_day = datetime.date.today()
                orc_figures = fetch_orc_stats(WAR_DAYS, TIMEOUT * 2)

            # Once per hour tasks
            if ( (last_update_hour != this_hour)):
                if datetime.datetime.now().minute > 30: # Runs halfway through the hour
                    last_update_hour = this_hour
                    weather = fetch_weather(1.0)

            if '°' not in weather: notice('WARNING',f'Weather missing.') 

        # Show headlines
        news_size = 52
        for i in range(len(news)):
            # Flashes (using boolean inverse argument) every other second if keyword found in headline
            print_at(display, -16, 226 + ((news_size + 1) * i),
                        ' ' + news[i] + ' ', news_size, any(kw.lower() in news[i].lower(
                        ) for kw in WATCH_LIST) and (int(time.time()) % 2 == 0))

        # Show BTC and LTC values
        if btc_usd_spot >= 100000: print_at(display, WIN_W, 12, f"${btc_usd_spot // 1000:,.0f}.{btc_usd_spot % 1000 // 100:.0f}K", 204, True, 2)
        else: print_at(display, WIN_W, 12, f"${btc_usd_spot:,.0f}", 204, True, 2)

        pygame.draw.rect(display, white, pygame.Rect(WIN_W - 506, 226, 520, WIN_H - CHART_TOP))
        print_at(display, WIN_W, 227, f"H:${max(candles):,.0f}", 102, False, 2)  # BTC High
        print_at(display, WIN_W, 343, f"L:${min(candles):,.0f}", 102, False, 2)  # BTC Low

        print_at(display, WIN_W, WIN_H - 120, f"LTC:{ltc_btc_rate:,.4f}", 130, (ltc_btc_rate <= LTC_ALARM), 2)  # LTC
        pygame.draw.rect(display, (ltc_btc_rate <= LTC_ALARM), (WIN_W - 162, WIN_H - 120 - 32 - 8, 162, 8))
        print_at(display, WIN_W, WIN_H - 120 - 32, f"${(ltc_btc_rate * btc_usd_spot):.2f}".rjust(8) + ' ', 32, (ltc_btc_rate <= LTC_ALARM), 2) # LTC USD

        # Main chart
        draw_main_chart()

        # Show volatility indicator
        draw_volatility_indicator()

        # Show War Stats
        draw_war_stats()

        # Show badge
        display_image(display, BADGE, 881, CHART_BOTTOM + 16, 0.6)

        # Render scaled frame
        if(RESCALE_RESOLUTION != (WIN_W, WIN_H)): 
            rescaled_display = pygame.transform.smoothscale(display, RESCALE_RESOLUTION)
            rendered_display.blit(rescaled_display, (0, 0))
        else: rendered_display.blit(display, (0, 0))
        pygame.display.flip()

        clock.tick(FPS)

    stop_event.set()
    pygame.quit()
   
if __name__ == "__main__":
    shared_data = {'tasks': []}
    notice(TITLE,'Initialising...')

    try: 
        with open(os.path.join(LIBDIR, 'options.txt'),'r') as f:
            lines = f.readlines()
            line1, line2 = (''.join(c for c in line.strip() if c.isalnum() or c in " _-.,~'") for line in lines[:2]) # Sanitized
            LTC_ALARM = round(float(line1), 4)
            LOCATION = line2.title()
            notice('Options', f'Setting LTC threshold to : {LTC_ALARM}')
            notice('Options', f'Setting Location to `{LOCATION}`')
    except:
        notice('NOTICE',"Options are defaulting. \nYou are seeing this notice because there's a problem with your " + (os.path.join(LIBDIR,'options.txt')) + " file. \nTo set your options, ensure that it exists, is readable and has some newline-separated values for LTC threshold and location.")
        LTC_ALARM = 0.0040  # Below this ratio LTC display will be inverted
        LOCATION = 'New York' # For weather updates

    # Load watch words. Ignore any words containing non-printable characters  
    try: WATCH_LIST = [line.strip() for line in open(os.path.join(LIBDIR, 'watch-words.txt')) if all(char in string.printable for char in line)]
    except:
        notice('WARNING',"Watch word list is missing. \nYou are seeing this error because there's a problem with your {(os.path.join(LIBDIR,'watch-words.txt'))} file. Ensure that it exists, is readable and has some newline-separated watch words in it.")
        WATCH_LIST = ['breaking', 'shot', 'troop', 'explo', 'nuclear', 'chemical', 'Putin', 'killed', 'Moscow']
    btc_usd_spot = get_btc_spot_once(BTC_INTERVAL)
    while btc_usd_spot == 0:
        notice(TITLE, 'Please wait...')
        btc_usd_spot = get_btc_spot_once(BTC_INTERVAL)
        time.sleep(BTC_INTERVAL // 2)
    news = fetch_bbc_news(4)
    weather = fetch_weather()
    last_update_hour = int(time.strftime('%H'))
    orc_figures = fetch_orc_stats(WAR_DAYS, TIMEOUT*2)
    
    if RESCALE_RESOLUTION != (WIN_W, WIN_H): notice('Rescaling',str(RESCALE_RESOLUTION))

    notice(TITLE, 'Launching options service...')
    p = subprocess.Popen(['python','options.py'])
        
    notice(TITLE, 'Started')
    loop = asyncio.new_event_loop()
    stop_event = threading.Event()
    
    asyncio_thread = threading.Thread(target=run_asyncio_loop, args=(loop, stop_event, BTC_INTERVAL, LTC_INTERVAL, shared_data))
    asyncio_thread.start()

    # Run the Pygame loop in the main thread
    pygame_loop(stop_event)

    # Stop the asyncio loop and clean up
    cancel_tasks_and_stop_loop(loop, shared_data['tasks'])
    asyncio_thread.join()
    notice(TITLE, 'Ended')
