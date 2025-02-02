import requests
from datetime import datetime
import pytz
import tkinter as tk
from tkinter import Label

# Configuration de l'URL et des paramètres de l'API
url = 'https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux/estimated-timetable.json'
params = {
    'AccountKey': 'opendata-bordeaux-metropole-flux-gtfs-rt', # Clé d'accès à l'API
    'LineRef': 'bordeaux:Line:60:LOC', # Code pour le tram B
    'MonitoringRef': 'bordeaux:StopPoint:3733', # Arrêt Doyen Brus
    'DirectionRef': '0' # Direction cité du vin
}

# Stocker les heures estimées pour les conserver entre actualisations
stored_estimated_times = {}

# Création de la fenêtre principale
root = tk.Tk()
root.title("Prochains départs - Doyen Brus")
root.geometry("400x150")

# Création des labels pour afficher les horaires
labels = [Label(root, text="", font=("Helvetica", 12)) for _ in range(3)]
for label in labels:
    label.pack(pady=5) # Rajoute padding dans la fenêtre principale

def fetch_and_update():
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        current_time = datetime.now(pytz.timezone("Europe/Paris"))
        future_departures = []

        # Parcourir les données pour trouver les horaires de passage à l'arrêt Doyen Brus
        for entry in data.get('Siri', {}).get('ServiceDelivery', {}).get('EstimatedTimetableDelivery', []):
            for journey in entry.get('EstimatedJourneyVersionFrame', []):
                for vehicle_journey in journey.get('EstimatedVehicleJourney', []):
                    stop_info = vehicle_journey.get('EstimatedCalls', {}).get('EstimatedCall', [])
                    
                    for stop in stop_info:
                        stop_name = stop.get('StopPointName', [{}])[0].get('value')
                        if stop_name.lower() == "doyen brus":
                            aimed_arrival_time = stop.get('AimedArrivalTime')
                            expected_arrival_time = stop.get('ExpectedArrivalTime')
                            
                            # Conversion des heures au format local
                            if aimed_arrival_time:
                                aimed_arrival_time = datetime.strptime(aimed_arrival_time, "%Y-%m-%dT%H:%M:%SZ")
                                aimed_arrival_time = aimed_arrival_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/Paris"))
                            if expected_arrival_time:
                                expected_arrival_time = datetime.strptime(expected_arrival_time, "%Y-%m-%dT%H:%M:%SZ")
                                expected_arrival_time = expected_arrival_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/Paris"))

                            # Enregistrer l'heure estimée si elle est disponible, sinon conserver l'ancienne
                            stop_id = stop.get('StopPointRef', {}).get('value')
                            if expected_arrival_time:
                                stored_estimated_times[stop_id] = expected_arrival_time
                            elif stop_id in stored_estimated_times:
                                expected_arrival_time = stored_estimated_times[stop_id]

                            # Ajouter uniquement les horaires strictement futurs dans la liste
                            if aimed_arrival_time and aimed_arrival_time > current_time:
                                future_departures.append({
                                    "stop_name": stop_name,
                                    "aimed_arrival_time": aimed_arrival_time,
                                    "expected_arrival_time": expected_arrival_time
                                })
        
        # Trier la liste des départs futurs par ordre temporel
        future_departures.sort(key=lambda x: x["aimed_arrival_time"]) # Lambda agit comme un def de fonction

        # Mettre à jour les trois labels avec les trois prochains départs
        if future_departures:
            for i in range(3):
                if i < len(future_departures):
                    departure = future_departures[i]
                    aimed_arrival_time = departure['aimed_arrival_time']
                    expected_arrival_time = departure['expected_arrival_time']

                    # Utiliser l'heure estimée si disponible, sinon l'heure prévue
                    display_time = expected_arrival_time if expected_arrival_time else aimed_arrival_time
                    time_until_arrival = display_time - current_time
                    minutes = int(time_until_arrival.total_seconds() // 60)

                    # Calculer la différence entre l'heure prévue et l'heure estimée
                    if aimed_arrival_time != expected_arrival_time:
                        time_difference_seconds = (expected_arrival_time - aimed_arrival_time).total_seconds()
                        if abs(time_difference_seconds) >= 60:
                            time_difference_minutes = time_difference_seconds // 60
                            if time_difference_minutes > 0:
                                time_difference = f"en avance de {int(time_difference_minutes)} min"
                            else:
                                time_difference = f"retard de {abs(int(time_difference_minutes))} min"
                        else:
                            if time_difference_seconds > 0:
                                time_difference = f"en avance de {int(time_difference_seconds)} s"
                            else:
                                time_difference = f"retard de {abs(int(time_difference_seconds))} s"
                    else:
                        time_difference = "à l'heure"


                    # Afficher l'information formatée
                    labels[i].config(text=f"{departure['stop_name']} - Temps d'attente : {minutes} min (Heure : {display_time.strftime('%H:%M')}) ({time_difference})")
                else:
                    # Effacer les labels restants si moins de trois départs sont disponibles
                    labels[i].config(text="~ ~")
        else:
            # Si aucun départ n'est disponible, afficher "~ ~" sur chaque label
            for label in labels:
                label.config(text="~ ~")

    else:
        # Afficher un message d'erreur en cas d'échec de la requête
        for label in labels:
            label.config(text="Erreur : impossible de récupérer les données")

    # Reprogrammer la mise à jour toutes les 30 secondes
    root.after(30000, fetch_and_update)

# Initialiser la mise à jour
fetch_and_update()

# Lancer la boucle principale de l'interface
root.mainloop()
