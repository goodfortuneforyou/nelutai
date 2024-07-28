viber_data="{\"url\":\"\"}"
curl -X POST -H "X-Viber-Auth-Token: $viber_token" https://chatapi.viber.com/pa/set_webhook -d $viber_data