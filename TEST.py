import urllib.request
import json

def get_bch_hnl_fx():
    try:
        url = "https://bchapi-am.azure-api.net/api/v1/indicadores/97/cifras?formato=Json&reciente=1"

        hdr = {
            'Cache-Control': 'no-cache',
            'clave': 'd5f2cf52e4c0415195d3d05a84f7ceb2',
        }

        req = urllib.request.Request(url, headers=hdr)
        req.get_method = lambda: 'GET'
        response = urllib.request.urlopen(req)

        raw_data = response.read()  # Read once
        decoded_data = raw_data.decode('utf-8')  # Decode bytes to string
        json_data = json.loads(decoded_data)  # Parse JSON

        valor = json_data[0]['Valor']  # Extract the numeric value
        return valor

    except Exception as e:
        print("BCH FX ERROR - ", e)
        return None

x = get_bch_hnl_fx()