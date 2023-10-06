import requests
import jmespath
import json
import re

# Servicios 
api_core = "https://layer-api-core-service"
api_web = "https://layer-api-web-service"
api_capture = "https://layer-api-capture-service"

# Ambiente
tysonbeta = ".tysonbeta.com/v1/api"
prod = ".autonomation.tijuana.mesh-servicios-fnd.mx/v1/api"
ambiente = prod

config_vericuenta_bau = {
    "exp_formulario_stage": "veribanco",
    "exp_stage_list": "vericuenta",
    "exp_task_type": "MANUAL_T_SIACPQDISP",
    "exp_role": "vericuenta_calidad"
}

config_expedientes_suc = {
    "exp_formulario_stage": "captura",
    "exp_stage_list": "EXPEDIENTE_DIGITAL",
    "exp_task_type": "EXPEDIENTE_DIGITAL_SUC",
    "exp_role": "expedientes_calidad"
}

config_expedientes_cierre = {
    "exp_formulario_stage": "captura",
    "exp_stage_list": "EXPEDIENTE_DIGITAL",
    "exp_task_type": "EXPEDIENTE_DIGITAL_CIERRE",
    "exp_role": "expedientes_calidad"
}

config_expedientes_vericlient_suc = {
    "exp_formulario_stage": "vericlient",
    "exp_stage_list": "EXPEDIENTE_DIGITAL",
    "exp_task_type": "EXPEDIENTE_DIGITAL_SUC",
    "exp_role": "expedientes_calidad"
}

config_expedientes_vericlient_cierre = {
    "exp_formulario_stage": "vericlient",
    "exp_stage_list": "EXPEDIENTE_DIGITAL",
    "exp_task_type": "EXPEDIENTE_DIGITAL_CIERRE",
    "exp_role": "expedientes_calidad"
}

def original(description):
    description = description.replace(" ", "_")
    description = description.lower()
    description = normalize(description)
    return "original_" + description

def normalize(s):
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
    )
    for a, b in replacements:
        s = s.replace(a, b).replace(a.upper(), b.upper())
    return s

def row_by_description(description):
    return {
        "columnA": {
            "type": "",
            "nameValue": "",
            "servicePop": {},
            "defaultValue": description
        },
        "columnB": {
            "type": "answercw",
            "nameValue": description,
            "servicePop": {},
            "defaultValue": "NO SE ENCONTRÓ RESPUESTA"
        },
        "columnC": {
            "type": "client",
            "nameValue": original(description),
            "servicePop": {},
            "defaultValue": "NO SE ENCONTRÓ RESPUESTA"
        }
    }
    
def row_by_resolution(resolution):
    return {
        "columnA": {
            "type": "",
            "nameValue": "",
            "servicePop": {},
            "defaultValue": resolution.replace("original_", "").replace("_", " ")
        },
        "columnB": {
            "type": "client",
            "nameValue": resolution,
            "servicePop": {},
            "defaultValue": "NO SE ENCONTRÓ RESPUESTA"
        }
    }

def dict_2_json_str(d):
    d = str(d)
    d = d.replace("'", '"')
    d = d.replace("True", "true")
    d = d.replace("False", "false")
    return d

def new_order(order):
    return order+1000

def get_stage():
    
    global exp_stage_list
    global exp_task_type
    url = api_core + ambiente + "/getTaskStageList"
    x = requests.post(url, json={"task_identifier": exp_stage_list})
    x = x.json()
    x = x["tasks"]
    x = [task_stage for task_stage in x if task_stage["conditions"] == "{\"task_type\": \""+ exp_task_type +"\"}"][0]
    return x["id"], json.loads(x["stage_list"])[0]

def update_stage():
    global exp_stage_list
    global exp_task_type
    
    print(); print("Updating stage")
    _, stage_list = get_stage()
    new_result_conf = [stage_list["result_conf"][0]]
    ################################################################################################################### 
    new_result_conf[0]["service_call_postaction"] = "https://layer-api-core-service.tysonbeta.com/v1/api/dummy_callback"
    new_result_conf[0]["service_method_postaction"] = "POST"
    new_result_conf[0]["service_data_postaction"] = "data_result"
    new_result_conf[0]["result_action"] = 'answer'
    new_result_conf[0]["result_evaluation"] = 'data_result.codigoResolucion == \'ERROR\''
    new_result_conf[0]["result_action_data"]  = 'data_result'
    new_result_conf[0]["complete_result_data"] = "segment_extended_data"
    ###################################################################################################################
    stage_list["result_conf"] = new_result_conf

    new_task_config = []
    for task in stage_list["task_config"]:
        normal_task = dict(task)
        normal_task = get_task_config_from_stage_list(normal_task, is_reingesta = False)
        reingesta_task = dict(task)
        reingesta_task = get_task_config_from_stage_list(reingesta_task, is_reingesta = True)
        # Agregamos las tareas
        new_task_config.append(normal_task)
        new_task_config.append(reingesta_task)
        
    stage_list["task_config"] = new_task_config
    
    stage_list = [stage_list]
    
    exp_task_type = exp_task_type + "_CALIDAD"
    exp_stage_list = new_task_type 
    try:
        stage_id, _ = get_stage()
    except Exception:
        url = api_core + ambiente + "/add_task_stage_list"
        body = {
            "task_identifier": exp_stage_list,
            "conditions": "{\"task_type\": \""+ exp_task_type +"\"}",
            "stage_list": [],
            "active": True
        }
        x = requests.post(url, json=body)
        stage_id = x.json()["id"]
        
    url = api_core + ambiente + "/update_task_stage"
    body = {
        "id": stage_id,
        "stageList": json.dumps(stage_list)
    }
    x = requests.put(url, json=body)
    
    exp_task_type = exp_task_type.replace('_CALIDAD=', '')
        
    return x.json()

def get_task_config_from_stage_list(task, is_reingesta):
    
    task["role"] = exp_role
    if is_reingesta:
        try:
            del task["role"]  
        except Exception:
            "do nothing"      
    
    # Modificamos el order
    new_stage_order = task["stage_list"] 
    new_stage_order = new_stage_order.replace("stage=", "")
    new_stage_order = int(new_stage_order) + 1000
    new_stage_order = "stage=" + str(new_stage_order)
    task["stage_list"] = new_stage_order
    # Modificamos los service_call
    if "service_call_preaction" in task:
        task["service_call_preaction"] = "https://layer-api-core-service.tysonbeta.com/v1/api/dummy_callback"
        task["service_method_preaction"] = "POST"
    if "service_call_postaction" in task:
        task["service_call_postaction"] = "https://layer-api-core-service.tysonbeta.com/v1/api/dummy_callback" 
        task["service_method_postaction"] = "POST"
    # Modificamos los identificaodres
    task["microtask_identifier"] = task["microtask_identifier"] + " CALIDAD"
    if "qa_identifier" in task:
        task["qa_identifier"] = task["qa_identifier"] + " CALIDAD"
    if "task_identifier_data" in task and 'task_type' in task["task_identifier_data"]:
        task_identifier_data = str(task["task_identifier_data"])
        task_identifier_data = re.sub(r'task_type:[^,}]+', f'task_type:\'{exp_task_type + "_CALIDAD"}\'', task_identifier_data)
        task["task_identifier_data"] = task_identifier_data
        
    if "task_evaluation" in task:
        task_evaluation = str(task["task_evaluation"])
        if is_reingesta:
            task["task_evaluation"] = f"({task_evaluation}) && isReingestada"
        else:
            task["task_evaluation"] = f"({task_evaluation}) && !isReingestada"
        
    return task

def get_stage_list_original(stage):
    # 'stage_list': 'stage=1082' -> 82
    stage = stage.replace('stage=', '')
    stage = int(stage)
    stage = stage - 1000 if stage>1000 else stage
    return stage

def order_list(check_published = False):
    global exp_formulario_stage
    _, stage_list = get_stage()
    task_config = stage_list["task_config"]

    order_list = [get_stage_list_original(config["stage_list"]) 
                  for config in task_config]
    order_list = list(set(order_list))
    
    if check_published:
        # Revisamos que no se hayan publicado ya
        url = api_web + ambiente + "/get_stages"
        body = {"formulario": exp_formulario_stage}
        x = requests.post(url, json = body)

        # Realizamos una busqueda del stage que coincida con el order de entrada
        exp = "Stages[].Order"
        full_order_list = jmespath.search(exp, json.loads(x.text))
        
        order_list = [order for order in order_list if int(new_order(order)) not in full_order_list]
    
    print(order_list)
    return order_list

def delete_form(form_id):
    # Realizamos una llamada al layer-api-web para eliminar el cuestionario anterior
    url = api_web + ambiente + "/borrar_cuestionario"
    body = {
        "id": form_id
    }
    x = requests.post(url, json = body)
    if x.status_code == 200:
        print("El cuestionario previo ha sido eliminado")
    else:
        raise requests.exceptions.HTTPError(f"Error al eliminar el cuestionario previo: {x.status_code}")

def find_formulario_by_order(j, order):
    # Realizamos una busqueda del stage que coincida con el order de entrada
    exp = "Stages[].Order"
    order_list = jmespath.search(exp, j)
    idx = None
    try: 
        idx = order_list.index(order)
    except Exception as e:
        print(e)
        return 
    return j["Stages"][idx]    
    
def add_new_stage(order):
    global exp_formulario_stage
    # Hacemos una llamada al layer-api-web para obtener todos los stage de captura 
    url = api_web + ambiente + "/get_stages"
    body = {"formulario": exp_formulario_stage}
    x = requests.post(url, json = body)
    j = json.loads(x.text)

    formulario = find_formulario_by_order(j, order)
    if formulario == None:
        return "No se encontró el stage"
    
    # Encontramos los datos del formulario previo para remplazarlo
    prev_form_id = find_formulario_by_order(j, order+1000)
    if prev_form_id is not None:
        prev_form_id = prev_form_id["id"] if "CALIDAD" in prev_form_id["Nombre"] else None 
        delete_form(prev_form_id)
    else:
        print("No se encntró cuestionario previo")
    
    # A partir del formulario obtenemos datos importantes
    data = json.loads(formulario["Data"])
    verifications = data["verifications"]
    exp = "[?description != 'COMPARATIVA'].description"
    descriptions = jmespath.search(exp, verifications)

    # Creamos nuevas verificaciones, es decir una nuevas preguntas del cuestionario
    
     # Resolución original
     # Esta nueva pregunta contiene información de las preguntas anteriores
    resolutions = ['original_codigo_resolucion', 'original_codigo_respuesta', 'original_comentario_ejecutivo', 'original_comentario_resolucion']
    resolutions_verification = get_new_verification(
                         id=len(verifications)+1, 
                         description="RESOLUCIÓN", 
                         question=f"CALIDAD EN {exp_stage_list}".upper(), 
                         instructions="Revisa la resolución del agente original.", 
                         headings={
                                "columnA": "‍‍‍‍‍‎",
                                "columnB": "RESOLUCIÓN ORIGINAL"
                            }, 
                         rows = [row_by_resolution(resolution) for resolution in resolutions]
                        )
     
    # Añadimos la nueva pregunta
    verifications =  verifications + [resolutions_verification]
    
    # Realiza una comparación de tus respuesta
    comparativa_verification = get_new_verification(
                         id=len(verifications)+1, 
                         description="COMPARATIVA", 
                         question="Realiza una comparación de tus respuesta", 
                         instructions="Realiza una comparación de tus respuesta", 
                         headings={
                                "columnA": "PREGUNTA",
                                "columnB": "RESPUESTA ACTUAL",
                                "columnC": "RESPUESTA ORIGINAL"
                            }, 
                         rows=[row_by_description(description) for description in descriptions]
                        )
    
    # Añadimos la nueva pregunta
    resolutions_verification["id"] = len(verifications)+2
    verifications = verifications + [comparativa_verification]
    
    data["verifications"] = verifications
    
    # Realizamos una nueva llamada al layer-api-web para añadir nuestro nuevo cuestionario
    url = api_web + ambiente + "/agregar_cuestionario"
    body = {
        "name": formulario["Nombre"] + " CALIDAD", 
        "order": str(new_order(order)), 
        "formulario": exp_formulario_id,
        "data": dict_2_json_str(data)
    }
    x = requests.post(url, json = body)
    
    return x.text

def get_new_verification(id, description, question, instructions, headings, rows):
    new_verification = {
        "id": id,
        "input": {},
        "documents": [],
        "description": description,
        "conditionToHide": []
    }
    new_verification["input"] = {
        "question": question,
        "inputType": "empty",
        "nameValue": "",
        "answerType": "SI/NO",
        "defaultValue": "",
        "instructions": instructions,
        "optionalValue": False,
        "particularProperties": []
    }
    new_verification["input"]["particularProperties"] = [{
        "addType": "table",
        "addData": {
            "rows": rows,
            "headings": headings
        }
    }]
    
    return new_verification

if __name__ == "__main__":
    
    for i, config in enumerate([config_expedientes_vericlient_suc, config_expedientes_vericlient_cierre]):
        
        exp_formulario_stage = config["exp_formulario_stage"]
        exp_formulario_id = { "captura": "1", "verifisica": "2", "videollamada": "3", "vericuenta": "4", "vericlient": "5", "veribanco": "6", "creditAppViewer": "7" }
        exp_formulario_id = exp_formulario_id[exp_formulario_stage]
        exp_stage_list = config["exp_stage_list"]
        new_task_type = "calidad_" + exp_stage_list.lower() 
        exp_task_type = config["exp_task_type"]
        exp_role = config["exp_role"]
        
        print(i, exp_stage_list)
        for order in order_list():
            print(order)
            print(add_new_stage(order))
            print()
        print(update_stage())
        print()
