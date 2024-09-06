# This will not run on online IDE
# pylint: disable=invalid-name
# pylint: disable=consider-using-enumerate
from operator import contains
import requests
from ff_models import *
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import jsonpickle
from config import config_data
import sys, getopt
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import set_title
from prompt_toolkit.validation import Validator
import datetime

#TODO HIGH Add Output(json|excel) #json is done, but not part of a method
#TODO MED Make username, password, league id as inputs to module call
#TODO LOW Organize the methods a little better
#TODO VERY LOW I sort of want to utilize the objects in a web app for data manipulation/query
from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)

VERBOSE = True
def debug_print(message):
    """_summary_

    Args:
        message (_type_): _description_
    """
    if VERBOSE is True:
        print(message)

def debug_print_overwrite(message):
    LINE_UP = '\033[1A'
    LINE_CLEAR = '\x1b[2K'
    """_summary_

    Args:
        message (_type_): _description_
    """
    
    if VERBOSE is True:
        print(LINE_UP, end=LINE_CLEAR)
        print(message)
        

def connectTo(URL):
    webDriver = None

    try:
        service = Service('/snap/bin/chromium.chromedriver')
        webDriver = webdriver.Chrome(service=service)

        webDriver.get(URL)

    except Exception as e:
        print(e)
        if webDriver != None:
            webDriver.close()
            webDriver = None

    return webDriver

def get_driver():
    """_summary_

    Returns:
        _type_: _description_
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    # options.add_argument('--headless')
    return webdriver.Chrome(options)
    # return webdriver.Chrome()

def get_historical_data(driver, league):

    URL = f"https://fantasy.nfl.com/league/{league.id}/history"
    driver.get(URL)
    ships(driver, league)
    single_game_points(driver, league)
    single_player_points_leader(driver, league)
    points_leader(driver, league)
    add_teams_to_seasons(driver, league)
    get_schedules_and_rosters(driver, league)
    with open("league_"+league.id+".json", "w") as write_file:
        write_file.write(str(jsonpickle.encode(league)))
    #TODO: Getting a key error with adding playoffs. Need to revisit.
    #The playoff games are recorded as part of the schedule above, so
    #technically, you could do some calculations on when the playoffs
    #started and track a team through playoff games, and record validation
    #until this is fixed, the game_types won't distinguish between playoff
    #and consolation games in  post season.
    #add_playoffs(driver, league)
    with open("league_"+league.id+".json", "w") as write_file:
        write_file.write(str(jsonpickle.encode(league)))

def load_historical_data(league_id):
    with open("league_"+league_id+".json", "r") as read_file:
        league = jsonpickle.decode(read_file.read())
    return league

def open_main_page(username, password, leagueid, name, verbose):
    """Running this will run the entirety of the scrap. I've been using the debugger in 
    vscode
    """
    VERBOSE=verbose
    # driver = get_driver()
    URL = "https://id.nfl.com/account/sign-in"
    driver = connectTo(URL)
    debug_print(driver.title)
    # Wait until the email field is present
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, 'email-input-field'))
    )
    # Enter system
    email_field = driver.find_element(By.ID, 'email-input-field')
    email_field.send_keys(username)
    
    # click on continue
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Continue"]'))
    )
    continue_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="Continue"]')
    continue_btn.click()

    # Wait until the email field is present
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, 'password-input-field'))
    )
    # Enter system
    pw_field = driver.find_element(By.ID, 'password-input-field')
    pw_field.send_keys(password)
    
    # click on continue
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Sign In"]'))
    )
    signin_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="Sign In"]')
    signin_btn.click()

    league = League(name, leagueid)
    driver.implicitly_wait(2)

    return driver, league

def get_current_season_teams(driver, league) -> None:
    year = str(datetime.datetime.now().year)
    print(f"Working on {year} season")
    count = 0
    while True:
        URL = f"https://fantasy.nfl.com/league/{league.id}/owners"
        driver.get(URL)
        driver.implicitly_wait(3)
        owner_rows = driver.find_elements("xpath", "/html/body/div[1]/div[3]/div/div[1]/div/div/div/div[1]/div/table/tbody/tr")
        debug_print(f"{len(owner_rows)} teams in current season")
        if len(owner_rows) > 0:
            break
    
    for x in range(len(owner_rows)):
        # td[1]/div/a[2]
        team = get_team(owner_rows[x], "1", [])
        debug_print_overwrite(team.name)
        if count == 0:
            season = Season(year, team)
            league.update_season(season)
        else:
            season = league.seasons[year]
            season.add_team(team)
            league.update_season(season)
        count += 1
        
    # debug_print(f"{league.seasons}")
    return league


def ships(driver, league) -> None:
    """What it is all about, yachts and champagne

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    winner_rows = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[2]/div/div/div[1]/table/tbody/tr")
    debug_print("found")
    debug_print(str(len(winner_rows)))
    for x in range(len(winner_rows)):
        year = winner_rows[x].find_element("xpath",".//td[1]").text
        team = get_team(winner_rows[x], "3", [])
        ship = Championship(year)
        team.add_ship(ship)
        season = Season(year, team)
        league.update_season(season)
        debug_print(f"Year:{year} Name:{team.name} Id:{team.id}")
    debug_print(driver.title)
     
   
def single_game_points(driver, league) -> None:
    """Season Single Game Point Scoring leader

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    winner_rows = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[2]/div/div/div[2]/table/tbody/tr")
    debug_print("found")
    debug_print(str(len(winner_rows)))
    for x in range(len(winner_rows)):
        year = winner_rows[x].find_element("xpath",".//td[1]").text
        week = winner_rows[x].find_element("xpath",".//td[2]").text
        points = winner_rows[x].find_element("xpath",".//td[4]").text
        season = league.seasons[year]
        team = get_team(winner_rows[x], "3", season)
        season.set_highest_score(team.id, points, week)
        league.update_season(season)
        debug_print(f"Team:{team.name} Week:{season.highest_score_week} Score:{season.highest_score}")
    debug_print(driver.title)

def get_schedules_and_rosters(driver, league) -> None:
    """Adding each game directly to the individual team. It would be where
    I'd probably add rosters, but not messing with it atm

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    for year in league.seasons:
        season = league.seasons[year]
        for teamid in season.teams:
            debug_print(f"Working on {year} season - team {teamid}")
            #&gameSeason=year
            # 2646591
            url = "https://fantasy.nfl.com/league/"+league.id+"/history/"+year+"/schedule?standingsTab=schedule&scheduleType=team&leagueId="+league.id+"&scheduleDetail="+teamid
            driver.get(url)
            #driver.implicitly_wait(2)
            team = season.teams[teamid]
            #Could pull userId from class, unless the user no longer exists
            team.set_manager(driver.find_element("xpath", "//span[contains(@class,'userName')]").text)
            #Currently the only table on page, trying out the //
            game_rows = driver.find_elements("xpath", "//table/tbody/tr")
            for x in range(len(game_rows)):
                try:
                    week = game_rows[x].find_element("xpath", ".//td[1]").text
                    opp_team = get_team(game_rows[x], "2", season)
                    score = game_rows[x].find_element("xpath", ".//td[3]/div/a/em[1]").text
                    opponent_score = game_rows[x].find_element("xpath", ".//td[3]/div/a/em[2]").text
                    debug_print(f"{team.name} vs {opp_team.name} was {score}-{opponent_score}")
                    team.add_game(Game(week, team.name, team.id, score, opp_team.id, opp_team.name, opponent_score, "regular"))
                except Exception:
                    #Honestly this is sort of a guess, it happens in playoffs
                    team.add_bye_week(game_rows[x].find_element("xpath", ".//td[1]").text)

def single_player_points_leader(driver, league) -> None:
    """I planned on added players, but it felt like overkill. At least each season point
    scorer is recorded to the season

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    winner_rows = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[2]/div/div/div[3]/table/tbody/tr")
    debug_print("found")
    debug_print(str(len(winner_rows)))
    for x in range(len(winner_rows)):
        year = winner_rows[x].find_element("xpath",".//td[1]").text
        week = winner_rows[x].find_element("xpath",".//td[2]").text
        points = winner_rows[x].find_element("xpath",".//td[5]").text
        player_name = winner_rows[x].find_element("xpath",".//td[4]/div/a").text
        player_pos_team = winner_rows[x].find_element("xpath",".//td[4]/div/em").text
        season = league.seasons[year]
        team = get_team(winner_rows[x], "3", season)
        season.set_highest_player_score(team.id, points, week, player_name, player_pos_team)
        league.update_season(season)
        debug_print(f"Team:{team.name} Week:{week} Score:{points} PlayerName: {player_name} PlayerPos: {player_pos_team}")
    debug_print(driver.title)


def points_leader(driver, league) -> None:
    """Points leader is a single team each season..unless there is a tie then
    this is f'd

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    winner_rows = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[2]/div/div/div[4]/table/tbody/tr")
    debug_print("found")
    debug_print(str(len(winner_rows)))
    for x in range(len(winner_rows)):
        year = winner_rows[x].find_element("xpath",".//td[1]").text
        points = winner_rows[x].find_element("xpath",".//td[4]").text
        season = league.seasons[year]
        team = get_team(winner_rows[x], "3", season)
        season.set_points_leader(team.id, points)
        league.update_season(season)
        debug_print(f"Team:{team.name} Score:{season.highest_score}")
    debug_print(driver.title)

def add_playoffs(driver, league) -> None:
    """The playoffs are weird animal so made it an array of games on the season,
    and added the games to each team that played in them. Could mess up something with
    teams having exta games. Adding a boolean for isPlayoffs if that distinction needs
    to be made

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    for year in league.seasons:
        if int(year) < 2023:
            season = league.seasons[year]
            url = "https://fantasy.nfl.com/league/"+league.id+"/history/"+year+"/playoffs"
            driver.get(url)
            playoff_weeks = driver.find_elements("xpath","//ul[@class='playoffContent']/li")
            for x in range(len(playoff_weeks)):
                week = playoff_weeks[x].find_element("xpath", ".//h4").text.replace("Week", "").strip()
                playoff_games = playoff_weeks[x].find_elements("xpath", ".//ul/li")
                for y in range(len(playoff_games)):
                    week_title = playoff_games[y].find_element("xpath", ".//h5").text.strip()
                    game_type = "consolation" if "final" not in week_title or "Bowl" not in week_title else "playoff"
                    #playoff_games[y].find_element("xpath", ".//div/")
                    team = get_team_from_a(playoff_games[y].find_element("xpath", ".//div/div[1]/div[1]/a"), season)
                    score = playoff_games[y].find_element("xpath", ".//div/div[1]/div[2]").text
                    opp_team = get_team_from_a(playoff_games[y].find_element("xpath", ".//div/div[2]/div[1]/a"), season)
                    opp_score = playoff_games[y].find_element("xpath", ".//div/div[2]/div[2]").text
                    playoff_game = Game(week, team.name, team.id, score, opp_team.id, opp_team.name, opp_score, game_type)
                    season.add_playoff_game(playoff_game)
                    debug_print(f"{team.name} vs {opp_team.name} was {score}-{opp_score}")
                #TODO: Consider ensuring any other games not in playoffs set as toilet bowl or something
            league.update_season(season)

def add_teams_to_seasons(driver, league) -> None:
    """Adding the teams individually to a season

    Args:
        driver (_type_): _description_
        league (_type_): _description_
    """
    for year in league.seasons:
        season = league.seasons[year]
        url = "https://fantasy.nfl.com/league/"+league.id+"/history/"+year+"/standings?historyStandingsType=regular"
        count_divisions = -1
        driver.get(url)
        #driver.implicitly_wait(3)
        try:
            divisions = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[5]/div/div/div[contains(@class,'hasDivisions')]")
            count_divisions = len(divisions) - 1
            if count_divisions == -1:
                count_divisions = 1
        except Exception:
            debug_print("add_teams_to_seasons potential error: "+year)
        
        for division_index in range(count_divisions):
            if count_divisions == 1:
                rows = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[5]/div/div/div[1]/table/tbody/tr")
                division = ""
            else:
                #Selenium doesn't zero index..gross
                rows = driver.find_elements("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[5]/div/div/div["+str(division_index+2)+"]/table/tbody/tr")
                retval = driver.find_element("xpath","/html/body/div[1]/div[3]/div/div[1]/div/div[5]/div/div/div["+str(division_index+2)+"]/h5").text
                debug_print(retval)
                if ':' in retval:
                    division = retval.split(':')[1].strip()
                else:
                    division = retval.strip()
            team_count = len(rows)
            debug_print("current teams: " +str(len(season.teams)))
            for x in range(team_count):
                rank = rows[x].find_element("xpath",".//td[1]").text
                record = rows[x].find_element("xpath",".//td[3]").text
                points_for = rows[x].find_element("xpath",".//td[6]").text
                points_against = rows[x].find_element("xpath",".//td[7]").text
                team = get_team(rows[x], "2", season)
                if team.id in season.teams:
                    team = season.teams[team.id]
                team.add_record(record, points_for, points_against, rank, division)
                season.teams[team.id] = team
                debug_print(f"Team:{team.name} Points for: {points_for} Points Against:{points_against} Record: {record}")
            league.update_season(season)
        debug_print(driver.title)


def get_team(row, col, season, container = "td") -> Team:
    """Pulling the team name and id out of the expected column

    Args:
        row (_type_): _description_
        col (_type_): _description_
        season (_type_): _description_

    Returns:
        _type_: _description_
    """
    team_a = row.find_element("xpath",".//"+container+"["+col+"]/div/a[2]")
    return get_team_from_a(team_a, season)

def get_team_from_a(atag, season) -> Team:
    """_summary_

    Args:
        atag (_type_): _description_
        season (_type_): _description_

    Returns:
        _type_: _description_
    """
    team_id = atag.get_attribute("href").split('/')[-1]
    # Into earlier seasons the urls were a bit different
    if "teamId=" in team_id:
        team_id = team_id.split('teamId=')[1]
    try:
        return season.teams[team_id]
    except Exception:
        return Team(team_id, atag.text)

def get_league_settings(driver, league):
    config_settings = {}
    URL = f"https://fantasy.nfl.com/league/{league.id}/settings"
    driver.get(URL)
    driver.implicitly_wait(5)
    debug_print(driver.title)
    config_items = driver.find_elements("xpath", '//li[contains(@class, "nameValue")]')
    debug_print(f"Found {len(config_items)} config settings")

    for x in range(len(config_items)):
        row = config_items[x]
        config_name = row.find_element("xpath", "em").text
        config_val = row.find_element("xpath", "div").text
        config_settings[config_name.strip()] = config_val.strip()
        
    return

def get_week_games(driver, league, year, week) -> None:
    URL = f"https://fantasy.nfl.com/league/{league.id}?scheduleDetail={week}&scheduleType=week&standingsTab=schedule"
    driver.get(URL)
    driver.implicitly_wait(3)
    games = driver.find_elements("xpath", '//li[contains(@class, "matchup ")]')
    debug_print_overwrite(f"{len(games)} games found for week {week}")
    for x in range(len(games)):
        game = games[x]
        team_1 = game.find_element("xpath", 'div[contains(@class, "teamWrap-1")]')
        team_1_name = team_1.find_element("xpath", 'a').text
        team_1_href = team_1.find_element("xpath", 'a').get_attribute('href')
        team_1_id = team_1_href[team_1_href.rfind('/') + 1:].strip()
        #debug_print(f"{team_1_name} ({team_1_id})")
        team_1_score = team_1.find_element("xpath", 'div[contains(@class, "teamTotal")]').text
        #debug_print(team_1_score)
        team_2 = game.find_element("xpath", 'div[contains(@class, "teamWrap-2")]')
        team_2_name = team_2.find_element("xpath", 'a').text
        team_2_href = team_2.find_element("xpath", 'a').get_attribute('href')
        team_2_id = team_2_href[team_2_href.rfind('/') + 1:].strip()
        #debug_print(f"{team_2_name} ({team_2_id})")
        team_2_score = team_2.find_element("xpath", 'div[contains(@class, "teamTotal")]').text
        #debug_print(team_2_score)
        
        game = Game(week, team_1_name, team_1_id, team_1_score, team_2_id, team_2_name, team_2_score)
        league.seasons[str(year)].teams[team_1_id].add_game(game)
        game = Game(week, team_2_name, team_2_id, team_2_score, team_1_id, team_1_name, team_1_score)
        league.seasons[str(year)].teams[team_2_id].add_game(game)
    return league

def main_page() -> None:
    """_summary_
    """
    URL = "https://id.nfl.com/account/sign-in?authReturnUrl=https%3A%2F%2Fid.nfl.com%2Faccount"
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"}
    r = requests.get(url=URL, headers=headers)
    #r = requests.get(URL)
    
    soup = BeautifulSoup(r.content, 'html5lib') # If this line causes an error, run 'pip install html5lib' or install html5lib
    # debug_print(soup.prettify())
    # Here the user agent is for Edge browser on windows 10. You can find your browser user agent from the above given link.

def calculate_coaching_efficiency(team):
    players = team['players']
    potential_score = 0
    required_positions = ['QB', 'RB', 'WR', 'WR', 'TE', 'K', 'DEF', 'W/R/T', 'W/R/T']
    
    # put all the players into a temporary sorted list by their score
    players.sort(key=lambda x: x['score'], reverse=True)
    
    # for each required position, find the player with the highest score
    # and add their score to the potential score and remove that player from the player list
    for pos in required_positions:
        # debug_print(f"Working on {pos}")
        for player in players:
            if pos == 'W/R/T' and (player['position'] == 'WR' or player['position'] == 'RB' or player['position'] == 'TE'):
                potential_score += player['score']
                players.remove(player)
                # debug_print(f"used {player['name']} ({player['position']}) for {player['score']} points")
                break
            elif player['position'] == pos:
                potential_score += player['score']
                players.remove(player)
                # debug_print(f"used {player['name']} ({player['position']}) for {player['score']} points")
                break
    if potential_score == 0:
        return 0
    else:
        return (team['total_score'] / potential_score)

def calculate_luck_scores(league, season, week, weekly_team_details):
    team_ids = weekly_team_details.keys()
    luck_info = {}
    
    for team_id in team_ids:
        season = league.get_season(season.year)
        team = season.teams[team_id]
        game = team.games[str(week)]
        opponent_team_id = game.opponent_id
        
        data = {
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "outcome": 0
        }
        for other_team_id in team_ids:
            if other_team_id != team_id:
                if weekly_team_details[team_id]['total_score'] > weekly_team_details[other_team_id]['total_score']:
                    data['wins'] += 1
                elif weekly_team_details[team_id]['total_score'] < weekly_team_details[other_team_id]['total_score']:
                    data['losses'] += 1
                else:
                    data['ties'] += 1
                    
       
                
        if weekly_team_details[team_id]['total_score'] > weekly_team_details[opponent_team_id]['total_score']:
            data['outcome'] = 1
            luck = (data['losses'] + data['ties']) / (len(team_ids) - 1) * 100
        else:
            luck = 0 - (data['wins'] + data['ties']) / (len(team_ids) - 1) * 100
                
        luck_info[team_id] = luck
            
    return luck_info

def get_current_season_schedule(driver, league, year):
    season = league.get_season(str(year))
    for week in range(1, 14):
        league = get_week_games(driver, league, year, week)
    
    return league 

def process_nfl_game_center(driver, league, year, week):
    """_summary_

    Args:
        driver (object): WebDriver for Selenium
        league (object): league object
        season (int): season (year)
        week (int): game week
    """
    # Loop thru all teams in the league and get the game center info
    weekly_team_details = {}
    season = league.get_season(year)
    debug_print(f"Working on {year} season")
    for teamId in season.teams:
        team = {}
        team['id'] = teamId
        team['name'] = season.teams[teamId].name
        team['total_score'] = 0
        team['players'] = []
        last_count = 0
        total_score = 0
        URL = f"https://fantasy.nfl.com/league/{league.id}/team/{teamId}/gamecenter?week={week}"
        debug_print_overwrite(f"Navigating to {URL}")
        driver.get(URL)
        driver.implicitly_wait(3)
    
        players = driver.find_elements("xpath", '//tr[contains(@class, "player-")]')
        for player in players:
            weekly_pos = player.find_element("xpath", './/td[contains(@class, "teamPosition")]/span').text
            name = player.find_element("xpath", './/*[@class="playerNameAndInfo"]/div/a').text
            pos = player.find_element("xpath", './/*[@class="playerNameAndInfo"]/div/em').text.split(" - ")[0]
            score = float(player.find_element("xpath", './/td[contains(@class, "statTotal")]/span').text)
            if last_count < 1:
                total_score += score
            if "last" in player.get_dom_attribute("class"):
                last_count += 1
                team['total_score'] = total_score
            if last_count > 1:
                break
            team['players'].append({'name': name, 'position': pos, 'weekly_position': weekly_pos, 'score': score})
        # Calculate Coaching efficiency
        coaching_eff = calculate_coaching_efficiency(team)
        team['coaching_efficiency'] = coaching_eff
        weekly_team_details[teamId] = team
            
    # Calculate luck scores
    luck_scores = calculate_luck_scores(league, season, week, weekly_team_details)
    debug_print(weekly_team_details)
    debug_print(luck_scores)
    return

def process_historical_nfl_game_center(driver, league, year, week):
    """_summary_

    Args:
        driver (object): WebDriver for Selenium
        league (object): league object
        season (int): season (year)
        week (int): game week
    """
    # Loop thru all teams in the league and get the game center info
    weekly_team_details = {}
    season = league.get_season(year)
    debug_print(f"Working on {year} season")
    for teamId in season.teams:
        team = {}
        team['id'] = teamId
        team['name'] = season.teams[teamId].name
        team['total_score'] = 0
        team['players'] = []
        last_count = 0
        total_score = 0
        URL = f"https://fantasy.nfl.com/league/{league.id}/history/{season.year}/teamgamecenter?teamId={teamId}&week={week}"
        debug_print(f"Navigating to {URL}")
        driver.get(URL)
        driver.implicitly_wait(3)
    
        players = driver.find_elements("xpath", '//tr[contains(@class, "player-")]')
        for player in players:
            weekly_pos = player.find_element("xpath", './/td[contains(@class, "teamPosition")]/span').text
            name = player.find_element("xpath", './/*[@class="playerNameAndInfo"]/div/a').text
            pos = player.find_element("xpath", './/*[@class="playerNameAndInfo"]/div/em').text.split(" - ")[0]
            score = float(player.find_element("xpath", './/td[contains(@class, "statTotal")]/span').text)
            if last_count < 1:
                total_score += score
            if "last" in player.get_dom_attribute("class"):
                last_count += 1
                team['total_score'] = total_score
            if last_count > 1:
                break
            team['players'].append({'name': name, 'position': pos, 'weekly_position': weekly_pos, 'score': score})
        # Calculate Coaching efficiency
        coaching_eff = calculate_coaching_efficiency(team)
        team['coaching_efficiency'] = coaching_eff
        weekly_team_details[teamId] = team
            
    # Calculate luck scores
    luck_scores = calculate_luck_scores(league, season, week, weekly_team_details)
    debug_print(weekly_team_details)
    debug_print(luck_scores)
    return

def is_valid_email(text):
    """_summary_

    Args:
        text (_type_): _description_

    Returns:
        _type_: _description_
    """
    return "@" in text


validator = Validator.from_callable(
    is_valid_email,
    error_message="Not a valid e-mail address (Does not contain an @).",
    move_cursor_to_end=True,
)

def main(args):
    """_summary_

    Args:
        args (_type_): _description_

    Returns:
        _type_: _description_
    """
    email = password = l_id = l_name = None
    verbose = True
    reload = False
    try:
        opts, args = getopt.getopt(args,"qhe:p:i:n",["email=","password=","id=","name="])
    except getopt.GetoptError:
        print('Issue with input validate your format is like below')
        print('main.py -e <email> -p <password> -i <id> -n <name> [-q]')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('NFL Scraper will scrap NFL.COM to get your league history. Ensure you use the format below. \n')
            print('main.py -e <email> -p <password> -i <id> -n <name> [-q]')
            sys.exit()
        elif opt == "-q":
            verbose = False
        elif opt in ("-e", "--email"):
            email = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-i", "--id"):
            l_id = arg
        elif opt in ("-n", "--name"):
            l_name = arg
        elif opt in ("-r", "--reload"):
            reload = True
        else:
            print('main.py -e <email> -p <password> -i <id> -n <name> [-q]')
            print(f'{arg} unexpected, remove option and try again')
            sys.exit(1)
    if email is None:
        # email = prompt("Enter e-mail address: ", validator=validator, validate_while_typing=False)
        email = config_data['username']
    if password is None:
        # password = prompt("Password: ", is_password=True)
        password = config_data['password']
    if l_id is None:
        #l_id = prompt("Input League Id: ")
        l_id = config_data['league_id']
    if l_name is None:
        # l_name = prompt("Input the name of the league: ")
        l_name = config_data['league_name']
    driver, league = open_main_page(email, password, l_id, l_name, verbose)
    if reload:
        get_league_settings(driver, league)
        get_historical_data(driver, league)
    else:
        league = load_historical_data(l_id)
        league = get_current_season_teams(driver, league)
        league = get_current_season_schedule(driver, league, 2024)
        
    # get_week_games(driver, league, 2024, 1)
    process_nfl_game_center(driver, league, 2024, 1)
    return 1


if __name__ == "__main__":
    set_title("Enter nfl.com email, password, leaugeid, and any name")
    main(sys.argv[1:])
