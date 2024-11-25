# InstaDynamo 

## Setup Instructions (on local machines)

1. There are 3 types of apps to run:
    - Backend application
    - Dynamo control panel 
    - Dynamo Node Instance (depneding on the numebr of instances required)

2. Clone the repository
```bash
git clone https://github.com/Brian-1402/insta-dynamo.git
cd insta-dynamo
```

3. In 3 seperate terminals (on the same machine) run the following sub applications


    - Backend Application
    ```bash
    cd ./backend/src
    bash run.sh
    ```

    - Dynamo Control Panel
    ```bash
    cd ./dynamo_control_panel
    bash run.sh
    ```

    - dynamo_node
    ```bash
    cd ./dynamo_node
    bash run.sh
    ```

4. You will observe the following:
- The insta-dynamo app should now be running at http://0.0.0.0:9000
- The dynamo_control_panel will be running at http://localhost:8000
- One instance of Dynamo Node will also be running with host ip: 0.0.0.0 and port: 9090

5. Go to [dynamo_control_panel](http://localhost:8000) and add the dynamo node that has been created (node-id: "default_node", host: "0.0.0.0", port: "9090")

6. You can now see that the node has been added under the ring status tab. At the same time you can also access the [insta-dynamo](http://0.0.0.0:9000) app and register and start uploading images along with viewing them

7. For adding new nodes, the following command template should be used (in a new terminal) and then the same details should be filled in the [dynamo_control_panel](http://localhost:8000)
    ```bash
    cd dynamo_node
    NODE_ID=<node_name> uvicorn app.main:app --host <host> --port <port> --reload
    ```


## Setup Instructions (deployment)

1. The above instructions all ran the apps on the local host with predefined ports.
2. In case you wish to run the setup in a deployment mode, you will have to change the ports and ip's specified in the run.sh files according to your requirements
3. [Extra] You can also install postgresql and create a database for running the applications (default is sqllite3)
4. You will also need to create a .env file in the backend/ directory and populate it with the following:
```.env
IMAGE_SERVICE_IP=<ip_of_dynamo_control_panel>
IMAGE_SERVICE_PORT=<port_of_dynamo_control_panel>
DATABASE_URL=postgresql://<database_user_name>:<pw>@<host>/<database>
```
5. The remaining steps are same as before.