import json
import os
import pathlib
import shutil
import zipfile
from io import BytesIO
from pprint import pprint
from urllib.request import urlretrieve

import requests

LORE_NAMES = [
    'Acrobatics',
    'Arcana',
    'Athletics',
    'Crafting',
    'Deception',
    'Diplomacy',
    'Intimidation',
    'Medicine',
    'Nature',
    'Occultism',
    'Performance',
    'Religion',
    'Society',
    'Stealth',
    'Survival',
    'Thievery'
]


def clean():
    list_of_files = [
        "module.json",
        "module_1.json",
        "module_2.json",
        "system.json"
    ]
    for file_name in list_of_files:
        if os.path.exists(file_name):
            os.remove(file_name)


# def read_leveldb_to_json(leveldb_path, output_json_path):
#     # Otwórz bazę danych LevelDB
#     db = plyvel.DB(leveldb_path, create_if_missing=False)
#
#     # Inicjalizuj słownik do przechowywania danych
#     data = {}
#
#     # Iteruj przez wszystkie elementy w bazie danych
#     for key, value in db:
#         # Zakładamy, że klucze i wartości są zakodowane jako UTF-8
#         data[key.decode('utf-8')] = value.decode('utf-8')
#
#     # Zamknij bazę danych
#     db.close()
#
#     # Zapisz dane do pliku JSON
#     with open(output_json_path, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)


def exclude_empty_prerequisites(input_dict):
    if isinstance(input_dict, dict):
        result_dict = input_dict.copy()

        for key, value in input_dict.items():
            if key == "prerequisites" and isinstance(value, dict) and value.get("value") == []:
                result_dict.pop(key, None)
            elif isinstance(value, (dict, list)):
                result_dict[key] = exclude_empty_prerequisites(value)

        return result_dict
    elif isinstance(input_dict, list):
        return [exclude_empty_prerequisites(item) for item in input_dict]
    else:
        return input_dict


def sort_entries(input_dict):
    if "entries" in input_dict:
        input_dict["entries"] = dict(sorted(input_dict["entries"].items()))

    for key, value in input_dict.items():
        if isinstance(value, dict):
            input_dict[key] = sort_entries(value)

    return input_dict


def remove_empty_values(input_dict):
    if isinstance(input_dict, dict):
        # Kopiowanie słownika, aby nie modyfikować oryginalnego
        result_dict = input_dict.copy()

        # Rekurencyjne usuwanie pustych wartości
        for key, value in input_dict.items():
            if value is None or (isinstance(value, (dict, list)) and not value):
                result_dict.pop(key, None)
            elif isinstance(value, dict):
                result_dict[key] = remove_empty_values(value)
            elif isinstance(value, list):
                result_dict[key] = [remove_empty_values(item) for item in value]

        return result_dict
    elif isinstance(input_dict, list):
        # Rekurencyjne usuwanie pustych wartości z listy
        return [remove_empty_values(item) for item in input_dict]
    else:
        # Zwróć niezmienioną wartość, jeśli nie jest to ani słownik, ani lista
        return input_dict


def download_and_extract_zip(zip_url, zip_filename, extract_folder):
    response = requests.get(zip_url)

    with open(zip_filename, 'wb') as zip_file:
        zip_file.write(response.content)

    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)


def convert_extension(file_path, old_extension, new_extension):
    old_file = os.path.join(file_path, f"{old_extension}.db")
    new_file = os.path.join(file_path, f"{new_extension}.json")

    # Wczytaj zawartość z pliku
    with open(old_file, 'r') as file:
        data = file.read()
    # Zamień znaki nowej linii między obiektami na przecinki
    data = data.strip().replace('\n', ',\n')

    # Dodaj kwadratowe nawiasy, aby uzyskać poprawny format listy obiektów JSON
    json_data = f'[{data}]'

    # Wczytaj dane JSON
    parsed_data = json.loads(json_data)

    # Zapisz dane do pliku JSON
    with open(new_file, 'w') as outfile:
        json.dump(parsed_data, outfile, indent=4)

    os.remove(old_file)


def create_version_directory(version):
    if os.path.exists(version):
        print(f'Katalog {version} istnieje, pomijam tworzenie.')
        return False
    else:
        print(f'Tworzę katalog {version}', end="")
        os.makedirs(version)
        return True


def process_files(folder, version, type_system):
    dict_key = []
    exeptions = []
    for root, dirs, files in os.walk(folder):
        if "equipment.json" in files:
            files.insert(0, files.pop(files.index("equipment.json")))
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                print('Oryginalny plik:', file)
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)

                try:
                    compendium = data[0]
                except (KeyError, AttributeError) as e:
                    compendium = data

                keys = compendium.keys()
                print('Klucze pliku JSON:', list(keys))
                if '_id' not in keys and type_system == 'system':
                    print('Inny plik, pomiń')
                    shutil.copy(file_path, version)
                    continue

                # Dla folderów
                if 'color' in keys:
                    continue
                try:
                    name = compendium['_stats']['compendiumSource'].split('.')
                    new_name = fr'{version}\{name[1]}.{name[2]}.json'
                except KeyError:
                    new_name = fr'{version}\pf2e.{file}'
                if type_system.startswith('pf2e'):
                    new_name = fr'{version}\{type_system}.{file}'
                print('Nowy plik:', new_name)
                print()

                if pathlib.Path(f'{root}/{file.split(".")[0]}_folders.json').is_file():
                    transifex_dict = {
                        "label": file.split('.')[0].title(),
                        "folders": {},
                        "entries": {},
                        "mapping": {}
                    }

                    with open(f'{root}/{file.split(".")[0]}_folders.json', 'r', encoding='utf-8') as json_file:
                        data_folder = json.load(json_file)

                    for new_data in data_folder:
                        name = new_data["name"].strip()
                        transifex_dict["folders"].update({name: name})
                else:
                    transifex_dict = {
                        "label": file.split('.')[0].title(),
                        "entries": {},
                        "mapping": {}
                    }
                if file == 'spells.json':
                    transifex_dict["mapping"].update(
                        {
                            "areadetails": "system.area.details",
                            "cost": "system.cost.value",
                            "duration": "system.duration.value",
                            "range": "system.range.value",
                            "requirements": "system.requirements",
                            "target": "system.target.value",
                            "time": "system.time.value",
                            "primarycheck": "system.ritual.primary.check",
                            "secondarycheck": "system.ritual.secondary.checks",
                            "gmNote": "system.description.gm",
                            "heightening": {
                                "converter": "translateHeightening",
                                "path": "system.heightening.levels"
                            },
                            "spellVariants": {
                                "converter": "translateSpellVariant",
                                "path": "system.overlays"
                            }
                        }
                    )

                flag = []
                for new_data in data:
                    name = new_data["name"].strip()
                    # Dla Kompendium bez opisu
                    if 'items' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})

                    # Dla Makr
                    elif 'command' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})

                    # Dla Dzienników
                    elif 'pages' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        transifex_dict["entries"][name].update({"pages": {}})
                        for result in new_data['pages']:
                            transifex_dict["entries"][name]['pages'].update({result['name']: {}})
                            transifex_dict["entries"][name]['pages'][result['name']].update({"name": result['name']})
                            transifex_dict["entries"][name]['pages'][result['name']].update(
                                {"text": result['text']['content']})

                    elif 'permission' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        transifex_dict["entries"][name].update({"pages": {}})
                        transifex_dict["entries"][name]['pages'].update({name: {}})
                        transifex_dict["entries"][name]['pages'][name].update({"name": name})
                        transifex_dict["entries"][name]['pages'][name].update({"text": new_data['content']})

                    # Dla tabel
                    elif 'displayRoll' in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        transifex_dict["entries"][name].update({"description": new_data['description']})
                        transifex_dict["entries"][name].update({"results": {}})
                        for result in new_data['results']:
                            result_name = f'{result["range"][0]}-{result["range"][1]}'
                            transifex_dict["entries"][name]['results'].update({result_name: result['text']})

                    # Dla Kompendium
                    elif 'items' not in keys:
                        transifex_dict["entries"].update({name: {}})
                        transifex_dict["entries"][name].update({"name": name})
                        if not new_data['system']['description']['value'].startswith('<p>@Localize'):
                            transifex_dict["entries"][name].update(
                                {"description": new_data['system']['description']['value']})

                    exeptions.append(name)
                    # ====================================================================================================
                    # ---GM Note---
                    try:
                        if new_data['system']['description']['gm']:
                            transifex_dict["entries"][name].update({"gmNote": new_data['system']['description']['gm']})
                            flag.append('gm')
                    except KeyError:
                        pass

                    if 'gm' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "gmNote": "system.description.gm"
                            }
                        )

                    # ---Rules---
                    transifex_dict["entries"][name].update({"rules": {}})
                    rule_id = 0
                    try:
                        for rules in new_data['system']['rules']:
                            try:
                                if (rules['text'] != ''
                                        and not rules['text'].startswith("PF2E")
                                        and not rules['text'].startswith("{item")
                                        and not '@Localize' in rules['text']):
                                    transifex_dict["entries"][name]["rules"].update({rule_id: {"text": rules['text']}})
                                    flag.append('rules')

                            except KeyError:
                                pass
                            try:
                                if rules['label'] != '' and not rules['label'].startswith("PF2E"):
                                    transifex_dict["entries"][name]["rules"].update(
                                        {rule_id: {"label": rules['label']}})
                                    flag.append('rules')

                            except KeyError:
                                pass
                            try:
                                if rules['choices'] != '':
                                    transifex_dict["entries"][name]["rules"].update({rule_id: {"choices": {}}})
                                    choice_id = 0
                                    try:
                                        if not rules.get('prompt').startswith("PF2E"):
                                            transifex_dict["entries"][name]["rules"][rule_id].update(
                                                {"prompt": rules['prompt']})
                                    except AttributeError:
                                        pass
                                    for choice in rules['choices']:
                                        try:
                                            if not choice['label'].startswith("PF2E"):
                                                transifex_dict["entries"][name]["rules"][rule_id]["choices"].update(
                                                    {choice_id: {"label": choice['label']}})
                                                flag.append('rules')
                                            choice_id += 1
                                        except TypeError:
                                            pass
                            except KeyError:
                                pass
                            rule_id += 1
                    except KeyError:
                        pass

                    if 'rules' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "rules": {
                                    "converter": "translateRules",
                                    "path": "system.rules"
                                }
                            }
                        )

                    # ---Trained Lore---
                    try:
                        if new_data['system']['trainedLore'] != "":
                            transifex_dict["entries"][name].update({"trainedLore": new_data['system']['trainedLore']})
                            flag.append('trainedLore')
                    except KeyError:
                        pass

                    if 'trainedLore' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "trainedLore": "system.trainedLore"
                            }
                        )

                    # ---Badges---
                    try:
                        transifex_dict["entries"][name].update({"badges": new_data['system']['badge']['labels']})
                        flag.append('badges')
                    except KeyError:
                        pass
                    except TypeError:
                        pass

                    if 'badges' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "badges": "system.badge.labels",
                            }
                        )

                    # ---Overrides---
                    try:
                        transifex_dict["entries"][name].update({"overrides": []})
                        overrides = new_data['system']['overrides']
                        flag_iter = 0
                        for override in overrides:
                            transifex_dict["entries"][name]["overrides"].append(override)
                            flag_iter += 1
                        flag.append('overrides')
                    except KeyError:
                        pass

                    if 'overrides' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "overrides": "system.overrides",
                            }
                        )

                    # ---Prerequisites---
                    try:
                        new_data = exclude_empty_prerequisites(new_data)
                        transifex_dict["entries"][name].update(
                            {"prerequisites": new_data['system']['prerequisites']['value']})
                        flag.append('prerequisites')
                    except KeyError:
                        pass

                    if 'prerequisites' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "prerequisites": "system.prerequisites.value",
                            }
                        )

                    # ---Actors with appearance, backstory and gender---
                    try:
                        if new_data['system']['details']['biography']['appearance'] != "":
                            transifex_dict["entries"][name].update(
                                {"appearance": new_data['system']['details']['biography']['appearance']})
                            flag.append('appearance')
                    except KeyError:
                        pass

                    if 'appearance' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "appearance": "system.details.biography.appearance",
                            }
                        )

                    try:
                        if new_data['system']['details']['biography']['backstory'] != "":
                            transifex_dict["entries"][name].update(
                                {"backstory": new_data['system']['details']['biography']['backstory']})
                            flag.append('backstory')
                    except KeyError:
                        pass

                    if 'backstory' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "backstory": "system.details.biography.backstory",
                            }
                        )

                    try:
                        if new_data['system']['details']['gender']['value'] != "":
                            transifex_dict["entries"][name].update(
                                {"gender": new_data['system']['details']['gender']['value']})
                            flag.append('gender')
                    except KeyError:
                        pass

                    if 'gender' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "gender": "system.details.gender.value",
                            }
                        )

                    # ---Hazard and NPC---
                    try:
                        if new_data['system']['details']['publicNotes'] != "":
                            transifex_dict["entries"][name].update(
                                {"publicNotes": new_data['system']['details']['publicNotes']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['privateNotes'] != "":
                            transifex_dict["entries"][name].update(
                                {"privateNotes": new_data['system']['details']['privateNotes']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['ac']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"acDetails": new_data['system']['attributes']['ac']['details']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['blurb'] != "":
                            transifex_dict["entries"][name].update({"blurb": new_data['system']['details']['blurb']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['allSaves']['value'] != "":
                            transifex_dict["entries"][name].update(
                                {"allSavesBonus": new_data['system']['attributes']['allSaves']['value']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['speed']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"speedsDetails": new_data['system']['attributes']['speed']['details']})
                            flag.append('bestiary')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['perception']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"sensesDetails": new_data['system']['perception']['details']})
                            flag.append('bestiary')
                    except (TypeError, KeyError) as e:
                        pass

                    try:
                        if new_data['system']['details']['languages']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"languagesDetails": new_data['system']['details']['languages']['details']})
                            flag.append('bestiary')
                    except (TypeError, KeyError) as e:
                        pass

                    if 'bestiary' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "publicNotes": "system.details.publicNotes",
                                "privateNotes": "system.details.privateNotes",
                                "acDetails": "system.attributes.ac.details",
                                "blurb": "system.details.blurb",
                                "hpDetails": "system.attributes.hp.details",
                                "allSavesBonus": "system.attributes.allSaves.value",
                                "speedsDetails": "system.attributes.speed.details",
                                "sensesDetails": "system.perception.details",
                                "languagesDetails": "system.details.languages.details"
                            }
                        )

                    try:
                        if new_data['system']['attributes']['hp']['details'] != "":
                            transifex_dict["entries"][name].update(
                                {"hpDetails": new_data['system']['attributes']['hp']['details']})
                            flag.append('hp')
                    except KeyError:
                        pass

                    if 'hp' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "hpDetails": "system.attributes.hp.details"
                            }
                        )

                    # ---Hazard---
                    try:
                        if new_data['system']['details']['description'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"descriptionHazard": new_data['system']['details']['description']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['disable'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"disable": new_data['system']['details']['disable']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['reset'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update({"reset": new_data['system']['details']['reset']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['routine'] != "" and new_data['type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"routine": new_data['system']['details']['routine']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['attributes']['stealth']['details'] != "" and new_data[
                            'type'] == 'hazard':
                            transifex_dict["entries"][name].update(
                                {"stealth": new_data['system']['attributes']['stealth']['details']})
                            flag.append('hazard')
                    except KeyError:
                        pass

                    if 'hazard' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "descriptionHazard": "system.details.description",
                                "disable": "system.details.disable",
                                "reset": "system.details.reset",
                                "routine": "system.details.routine",
                                "stealth": "system.attributes.stealth.details",
                            }
                        )
                    # ---Vehicles---
                    try:
                        if new_data['system']['details']['description'] != "" and new_data['type'] == 'vehicle':
                            transifex_dict["entries"][name].update(
                                {"description": new_data['system']['details']['description']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['crew'] != "":
                            transifex_dict["entries"][name].update({"crew": new_data['system']['details']['crew']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['pilotingCheck'] != "":
                            transifex_dict["entries"][name].update(
                                {"pilotingCheck": new_data['system']['details']['pilotingCheck']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    try:
                        if new_data['system']['details']['speed'] != "":
                            transifex_dict["entries"][name].update({"speed": new_data['system']['details']['speed']})
                            flag.append('vehicles')
                    except KeyError:
                        pass

                    if 'vehicles' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "description": "system.details.description",
                                "crew": "system.details.crew",
                                "pilotingCheck": "system.details.pilotingCheck",
                                "speed": "system.details.speed",
                            }
                        )

                    # === ITEMS ===
                    transifex_dict["entries"][name].update({"items": {}})
                    try:
                        for item in new_data['items']:
                            # Nazwanie klucza
                            if item['type'] in ['melee', 'ranged']:
                                try:
                                    type_name = f'strike-{item["system"]["weaponType"]["value"]}'
                                except KeyError:
                                    type_name = f'strike-{item['type']}'
                                    for trait in item["system"]["traits"]["value"]:
                                        if trait.startswith("range"):
                                            type_name = 'strike-ranged'
                            else:
                                type_name = item['type']
                            item_name = f'{type_name}->{item["name"]}'

                            # Jeśli zaklęcie, bierz tylko unikalne
                            if '(' in item['name']:
                                transifex_dict["entries"][name]['items'].update({item_name: {
                                    "name": item['name']
                                }})
                            if item['type'] == 'spell':
                                continue

                            # Jeśli akcja jest połączona z bronią, nie tłumacz
                            try:
                                propertly_link = True
                                if 'linkedWeapon' in item['flags']['pf2e']:
                                    for item2 in new_data['items']:
                                        if item2['_stats']['compendiumSource'].startswith('Compendium') and item2['_id'] == item['flags']['pf2e']['linkedWeapon'] and item['name'] in exeptions:
                                            propertly_link = False
                                            break
                                    if item['name'] == 'Shiv':
                                        propertly_link = True
                                    if propertly_link:
                                        transifex_dict["entries"][name]['items'].update({item_name: {
                                            "name": item['name']
                                        }})
                                    continue
                            except KeyError:
                                pass
                            except AttributeError:
                                pass

                            # Jeśli jest to Skill, sprawdź, czy to unikalna nazwa i czy są jakieś opcje
                            if item['type'] == 'lore':
                                if item['name'] not in LORE_NAMES:
                                    transifex_dict["entries"][name]['items'].update({item_name: {
                                        "name": item['name']
                                    }})
                                elif 'variants' in item['system'].keys():
                                    transifex_dict["entries"][name]['items'].update({item_name: {
                                        "skillVariants": {'0': {'label': item['system']['variants']['0']['label']}}}
                                    })
                                continue

                            # Jeśli przedmiot jest z istniejącej publikacji i nie jest przedmiotem z innego kompendium
                            try:
                                if (item['_stats']['compendiumSource'].startswith('Compendium')
                                        and item['system']['publication']['title'] != ""
                                        and '(' not in item['name'] and item['type'] != 'action'
                                        and item['name'] in exeptions):
                                    continue
                            except KeyError:
                                pass
                            except AttributeError:
                                pass

                            # Jeśli opis jest przetłumaczony, bierz tylko nazwę, w przeciwnym wypadku razem z opisem
                            if item['system']['description']['value'].startswith('<p>@Localize') or \
                                    item['system']['description']['value'] == "":
                                if item['name'] == 'Darkvision' or item['name'] == 'Low-Light Vision' or item[
                                    'name'] == 'Greater Darkvision':
                                    continue
                                transifex_dict["entries"][name]['items'].update({item_name: {
                                    "name": item['name'],
                                    "rules": {}
                                }})
                            else:
                                transifex_dict["entries"][name]['items'].update({item_name: {
                                    "name": item['name'],
                                    "description": item['system']['description']['value'],
                                    "rules": {}
                                }})

                            # Jeśli posiada rules, dodaj
                            if item.get('system', {}).get('rules'):
                                for index, rule in enumerate(item['system']['rules']):
                                    if not rule.get('label', '').startswith('PF2E') and rule.get('label') and not rule.get('label', '').startswith('{item'):
                                        transifex_dict["entries"][name]['items'][item_name]["rules"].update({index:{}})
                                        transifex_dict["entries"][name]['items'][item_name]["rules"][index].update({"label": rule.get('label')})

                                    if not rule.get('text', '').startswith('PF2E') and rule.get('text') and not rule.get('text', '').startswith('{item'):
                                        transifex_dict["entries"][name]['items'][item_name]["rules"].update({index:{}})
                                        transifex_dict["entries"][name]['items'][item_name]["rules"][index].update({"text": rule.get('text')})

                            flag.append('items')
                    except KeyError:
                        pass

                    if 'items' in flag:
                        transifex_dict['mapping'].update(
                            {
                                "items": {
                                    "converter": "translateActorItems",
                                    "path": "items"
                                },
                                "rules": {
                                    "converter": "translateRules",
                                    "path": "system.rules"
                                }
                            }
                        )

                    # SPELLS =============================================================================================
                    if file == 'spells.json':
                        name = new_data["name"].strip()

                        # AreaDetail
                        try:
                            transifex_dict["entries"][name].update(
                                {"areadetails": new_data['system']['area']['details']})
                        except (KeyError, TypeError):
                            pass

                        # Cost
                        if new_data['system']['cost']['value'] != "":
                            transifex_dict["entries"][name].update({"cost": new_data['system']['cost']['value']})

                        # Duration
                        if new_data['system']['duration']['value'] != "":
                            transifex_dict["entries"][name].update(
                                {"duration": new_data['system']['duration']['value']})

                        # Range
                        if new_data['system']['range']['value'] != "":
                            transifex_dict["entries"][name].update({"range": new_data['system']['range']['value']})

                        # Requirements
                        if new_data['system']['requirements'] != "":
                            transifex_dict["entries"][name].update({"requirements": new_data['system']['requirements']})

                        # Target
                        if new_data['system']['target']['value'] != "":
                            transifex_dict["entries"][name].update({"target": new_data['system']['target']['value']})

                        # Time
                        if new_data['system']['time']['value'] != "":
                            transifex_dict["entries"][name].update({"time": new_data['system']['time']['value']})

                        # Primary check
                        try:
                            if new_data['system']['ritual']['primary']['check'] != "":
                                transifex_dict["entries"][name].update(
                                    {"primarycheck": new_data['system']['ritual']['primary']['check']})
                        except KeyError:
                            pass
                        except TypeError:
                            pass

                        # Secondary check
                        try:
                            if new_data['system']['ritual']['secondary']['checks'] != "":
                                transifex_dict["entries"][name].update(
                                    {"secondarycheck": new_data['system']['ritual']['secondary']['checks']})
                        except KeyError:
                            pass
                        except TypeError:
                            pass

                        # Heightening
                        try:
                            if new_data['system']['heightening']['levels'] != "":
                                transifex_dict["entries"][name].update({"heightening": {}})
                                for level in new_data['system']['heightening']['levels']:
                                    transifex_dict["entries"][name]["heightening"].update({level: {}})
                                    for type_system in new_data['system']['heightening']['levels'][level]:
                                        if type_system == 'damage' or type_system == 'area':
                                            continue
                                        transifex_dict["entries"][name]["heightening"][level].update(
                                            {type_system:
                                                 new_data['system']['heightening']['levels'][level][type_system][
                                                     'value']})
                                transifex_dict = remove_empty_values(transifex_dict)
                        except KeyError:
                            pass

                        # spellVariants
                        try:
                            if new_data['system']['overlays'] != "":
                                transifex_dict["entries"][name].update({"spellVariants": {}})
                                for overlays in new_data['system']['overlays']:
                                    try:
                                        if new_data['system']['overlays'][overlays]['name'] != "":
                                            transifex_dict["entries"][name]["spellVariants"].update({overlays: {}})
                                            transifex_dict["entries"][name]["spellVariants"][overlays].update(
                                                {"name": new_data['system']['overlays'][overlays]['name']})
                                    except KeyError:
                                        pass

                        except KeyError:
                            pass

                transifex_dict = remove_empty_values(transifex_dict)
                transifex_dict = remove_empty_values(transifex_dict)
                transifex_dict = remove_empty_values(transifex_dict)
                transifex_dict = sort_entries(transifex_dict)
                with open(new_name, "w") as outfile:
                    json.dump(transifex_dict, outfile, indent=4)

                dict_key.append(f'{compendium.keys()}')

# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Ścieżka do pliku z wersją systemu
sys_url = "https://github.com/foundryvtt/pf2e/releases/latest/download/system.json"

path, headers = urlretrieve(sys_url, 'system.json')
version = json.loads(open('system.json', 'r', encoding='utf-8').read())["version"]
zip_url = "https://github.com/foundryvtt/pf2e/releases/latest/download/json-assets.zip"
extract_folder = 'pack'
print()
print("*** Wersja modułu PF2E: ", version, " ***")

zip_filename = "json-assets.zip"

if create_version_directory(version):
    download_and_extract_zip(zip_url, zip_filename, extract_folder)
else:
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons1
# Ścieżka do pliku z wersją addon1
# add_1_url = "https://github.com/reyzor1991/foundry-vtt-pf2e-action-support/releases/latest/download/module.json"
#
# path_1, headers_1 = urlretrieve(add_1_url, 'module_1.json')
# version_1 = 'addon_1_' + json.loads(open('module_1.json', 'r', encoding='utf-8').read())["version"]
# zip_addons1_filename = "pf2e-action-support.zip"
# zip_addons1 = 'https://github.com/reyzor1991/foundry-vtt-pf2e-action-support/releases/latest/download/pf2e-action-support.zip'
# extract_folder = 'pack_addon_1'
# print()
# print("*** Wersja dodatku_1 PF2E: ", version_1, " ***")
#
# if create_version_directory(version_1):
#     download_and_extract_zip(zip_addons1, zip_addons1_filename, extract_folder)
# else:
#     with zipfile.ZipFile(zip_addons1_filename, 'r') as zip_ref:
#         zip_ref.extractall(extract_folder)
#
# convert_extension(fr'{extract_folder}\pf2e-action-support\packs', "action-support", "action-support")
# convert_extension(fr'{extract_folder}\pf2e-action-support\packs', "action-support-macros", "action-support-macros")

# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons2
# Ścieżka do pliku z wersją addon2
# add_2_url = "https://github.com/JDCalvert/FVTT-PF2e-Ranged-Combat/releases/latest/download/module.json"
#
# path_2, headers_2 = urlretrieve(add_2_url, 'module_2.json')
# version_2 = 'addon_2_' + json.loads(open('module_2.json', 'r', encoding='utf-8').read())["version"]
# zip_addons2_filename = "pf2e-ranged-combat.zip"
# zip_addons2 = 'https://github.com/JDCalvert/FVTT-PF2e-Ranged-Combat/releases/latest/download/pf2e-ranged-combat.zip'
# extract_folder = 'pack_addon_2'
# print()
# print("*** Wersja dodatku_2 PF2E: ", version_2, " ***")
#
# if create_version_directory(version_2):
#     download_and_extract_zip(zip_addons2, zip_addons2_filename, extract_folder)
# else:
#     with zipfile.ZipFile(zip_addons2_filename, 'r') as zip_ref:
#         zip_ref.extractall(extract_folder)
#
# docs = list(parse_leveldb_documents(f'pack_addon_2/packs/effects/000005.ldb'))
# print(docs)
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===
# Addons3
# Ścieżka do pliku z wersją addon3
# add_3_url = "https://github.com/reyzor1991/foundry-vtt-pf2e-reaction/releases/latest/download/module.json"
#
# path_3, headers_3 = urlretrieve(add_3_url, 'module_3.json')
# version_3 = 'addon_3_' + json.loads(open('module_3.json', 'r', encoding='utf-8').read())["version"]
# zip_addons3_filename = "pf2e-reaction.zip"
# zip_addons3 = 'https://github.com/reyzor1991/foundry-vtt-pf2e-reaction/releases/latest/download/pf2e-reaction.zip'
# extract_folder = 'pack_addon_3'
# print()
# print("*** Wersja dodatku_3 PF2E: ", version_3, " ***")
#
# if create_version_directory(version_3):
#     download_and_extract_zip(zip_addons3, zip_addons3_filename, extract_folder)
# else:
#     with zipfile.ZipFile(zip_addons3_filename, 'r') as zip_ref:
#         zip_ref.extractall(extract_folder)
#
# convert_extension(fr'{extract_folder}\pf2e-reaction\packs', "reaction-effects", "reaction-effects")
# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===

# === === === === === === === === === === === === === === === === === === === === === === === === === === === === ===


folder = 'pack'
process_files(folder, version, 'system')

# folder = r'pack_addon_1\pf2e-action-support\packs'
# process_files(folder, version_1, 'pf2e-action-support')

# folder = r'pack_addon_2/output'
# process_files(folder, version_2, "pf2e-ranged-combat")

# folder = r'pack_addon_3\pf2e-reaction\packs'
# process_files(folder, version_3, "pf2e-reaction")

clean()
