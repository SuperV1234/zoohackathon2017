# Alert server



## Overview

* Reads the alerts from a `.csv` and monitors it in the background for updates

* Accepts `GET`/`POST` requests to query alerts and update their state

* Simulates dispatch logic to different targets *(groups of rangers)*

* Provides in-memory database for alert data



## API

* `GET` @ `url:port/?state=MY_STATE`

  Returns a JSON list of alerts whose state is `MY_STATE`.

* `POST` @ `url:port/`

  Arguments:

    * `uuid`: UUID of the alert to mutate.

    * `old_state`: expected current state of the alert.

    * `new_state`: new state of the alert.

  Returns a JSON object with the result *(`bool`)* of the state change.


