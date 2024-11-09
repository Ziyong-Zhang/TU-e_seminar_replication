import os
from pathlib import Path
import sys
from datetime import datetime

from ekg_creator.data_managers.interpreters import Interpreter
from ekg_creator.data_managers.semantic_header import SemanticHeader
from ekg_creator.database_managers.EventKnowledgeGraph import EventKnowledgeGraph
from ekg_creator.database_managers.db_connection import DatabaseConnection
from ekg_creator.data_managers.datastructures import ImportedDataStructures
from ekg_creator.utilities.performance_handling import Performance
from ekg_creator.database_managers import authentication

# Region Add some evaluation functions
def add_direct_follow_relations(db_connection, activity_pairs) -> None:
    """
    Adds DF_A relationships between activity pairs in the given list.
    """
    for act_1, act_2 in activity_pairs:
        db_connection._exec_query(
            f"MATCH (act1:Activity {{name:'{act_1}'}}) "
            f"MATCH (act2:Activity {{name:'{act_2}'}}) "
            f"CREATE (act1)-[:DF_A]->(act2)"
        )

def evaluate_results(db_connection, identifier_string, output_path: str = '') -> None:
    """
    Evaluates graph statistics, calculating completeness and consistency of DF_BOX relations.
    Results are saved to a text file.
    """

    # Query to count total unique boxes (representing individual traces)
    total_boxes_query = '''MATCH (b:Box) RETURN count(DISTINCT b)'''

    # Query to count incomplete traces where DF_A does not align with DF_BOX
    incomplete_boxes_query = '''MATCH (start:Event)-[:DF_BOX]->(end:Event)
    MATCH (start)-[:CORR]->(incomp_box:Box) WHERE (end)-[:CORR]->(incomp_box)
    MATCH (start)-[:OBSERVED]->(act1:Activity), (end)-[:OBSERVED]->(act2:Activity)
    WHERE NOT (act1)-[:DF_A]->(act2)
    RETURN count(DISTINCT incomp_box)'''

    # Query to find boxes with no DF_BOX relations
    no_trace_boxes_query = '''MATCH (b:Box)
    WHERE NOT EXISTS { MATCH (e:Event)-[:CORR]->(b) WHERE (e)-[:DF_BOX]->(:Event) }
    RETURN count(DISTINCT b)'''

    # Total DF_BOX relations and consistent DF_BOX with DF_A relations
    total_dfbox_query = '''MATCH ()-[dfb:DF_BOX]->() RETURN count(dfb)'''
    consistent_dfbox_query = '''MATCH (start:Event)-[dfb:DF_BOX]->(end:Event)
    MATCH (start)-[:OBSERVED]->(act1:Activity), (end)-[:OBSERVED]->(act2:Activity)
    WHERE (act1)-[:DF_A]->(act2)
    RETURN count(dfb)'''
    
    total_traces = list(db_connection._exec_query(total_boxes_query)[0].values())[0]
    incomplete_traces = list(db_connection._exec_query(incomplete_boxes_query)[0].values())[0]
    no_trace_boxes = list(db_connection._exec_query(no_trace_boxes_query)[0].values())[0]

    total_dfb_relations = list(db_connection._exec_query(total_dfbox_query)[0].values())[0]
    consistent_dfb_relations = list(db_connection._exec_query(consistent_dfbox_query)[0].values())[0]

    # Write results to the output file
    with open(f'{output_path}result_eval.txt', 'a') as result_file:
        completeness = 100 - ((incomplete_traces + no_trace_boxes) / total_traces * 100)
        consistency = consistent_dfb_relations / total_dfb_relations * 100
        result_file.write(f"{identifier_string}, {completeness}%, {consistency}%, ")

def record_runtime(start_time, end_time, output_path: str = '') -> None:
    duration = end_time - start_time
    with open(f'{output_path}result_eval.txt', 'a') as result_file:
        result_file.write(f': {duration}\n')

# Endregion

connection = authentication.connections_map[authentication.Connections.LOCAL]

# region ADDED IN REPLICATION
list_args = ['Example',
                'Generated_1',
                'Generated_2',
                'Generated_3',
                'Generated_4',
                'Noise_1',
                'Noise_2',
                'Noise_3',
                'Noise_4'
                ]

if len(sys.argv) == 1:
    argv = ''
elif sys.argv[1] not in list_args:
    raise Exception(f"{sys.argv[1]} not recognized as valid argument, please choose from the following: {list_args}")
else:
    argv = sys.argv[1]

relations = (('LoadAL','LoadFS'),
                 ('LoadFS','Fill'),
                 ('Fill','UnloadFS'),
                 ('UnloadFS','LoadSS'),
                 ('LoadSS','Seal'),
                 ('Seal','UnloadSS'),
                 ('UnloadSS','UnloadAL'))


dataset_name = f'BoxProcess{argv}'
semantic_header_path = Path(f'json_files/{dataset_name}.json')

query_interpreter = Interpreter("Cypher")
semantic_header = SemanticHeader.create_semantic_header(semantic_header_path, query_interpreter)
perf_path = os.path.join("", "perf", dataset_name, f"{dataset_name}Performance.csv")
number_of_steps = None

ds_path = Path(f'json_files/{dataset_name}_DS.json')
datastructures = ImportedDataStructures(ds_path)

# several steps of import, each can be switch on/off
step_clear_db = True
step_populate_graph = True
verbose = False  # print the used queries

db_connection = DatabaseConnection(db_name=connection.user, uri=connection.uri, user=connection.user,
                                   password=connection.password, verbose=verbose)


def create_graph_instance(perf: Performance) -> EventKnowledgeGraph:
    """
    Creates an instance of an EventKnowledgeGraph
    @return: returns an EventKnowledgeGraph
    """

    return EventKnowledgeGraph(db_connection=db_connection, db_name=connection.user,
                               specification_of_data_structures=datastructures, semantic_header=semantic_header,
                               perf=perf,
                               use_preprocessed_files=False)


def clear_graph(graph: EventKnowledgeGraph, perf: Performance) -> None:
    """
    # delete all nodes and relations in the graph to start fresh
    @param graph: EventKnowledgeGraph
    @param perf: Performance
    @return: None
    """

    print("Clearing DB...")
    graph.clear_db()
    perf.finished_step(log_message=f"Cleared DB")


def populate_graph(graph: EventKnowledgeGraph, perf: Performance):
    # Import the event data as Event nodes and location data as Location nodes and entity types from activity records as
    # region EntityTypes
    graph.import_data()
    perf.finished_step(log_message=f"(:Event), (:Location) and (:EntityType) nodes done")

    # for each entity, we add the entity nodes to graph and correlate them (if possible) to the corresponding events
    graph.create_entities_by_nodes()
    perf.finished_step(log_message=f"(:Entity) nodes done")

    graph.correlate_events_to_entities()
    perf.finished_step(log_message=f"[:CORR] edges done")

    # create the classes
    graph.create_classes()
    perf.finished_step(log_message=f"(:Activity) nodes done")

    # create [:PART_OF] and [:AT] relation
    graph.create_entity_relations_using_nodes()
    perf.finished_step(log_message=f"[:REL] edges done")

    graph.create_entity_relations_using_relations(relation_types=["LOADS", "UNLOADS", "ACTS_ON"])
    # endregion

    # region Infer missing information
    # rule c, both for preceding load events and succeeding unload events
    graph.infer_items_propagate_upwards_multiple_levels(entity_type="Box", is_load=True)
    graph.infer_items_propagate_upwards_multiple_levels(entity_type="Box", is_load=False)
    graph.create_entity_relations_using_relations(relation_types=["AT_POS"])
    # rule d
    graph.infer_items_propagate_downwards_multiple_level_w_batching(entity_type="Box",
                                                                    relative_position_type="BatchPosition")
    # rule b
    graph.infer_items_propagate_downwards_one_level(entity_type="Box")

    # endregion

    # region Complete EKG creation, add DF relations after missing correlations are inferred
    graph.create_df_edges()
    perf.finished_step(log_message=f"[:DF] edges done")
    # endregion

    # region ADDED IN REPLICATION, apply evaluation and save to result.txt
    if argv!='':
        add_direct_follow_relations(db_connection, relations)
        evaluate_results(db_connection,f"{argv}")
    # endregion

def main() -> None:
    """
    Main function, read all the logs, clear and create the graph, perform checks
    @return: None
    """
    start_time = datetime.now()
    # performance class to measure performance
    perf = Performance(perf_path, number_of_steps=number_of_steps)
    graph = create_graph_instance(perf)

    if step_clear_db:
        clear_graph(graph=graph, perf=perf)

    if step_populate_graph:
        populate_graph(graph=graph, perf=perf)

    perf.finish()
    perf.save()

    graph.print_statistics()

    db_connection.close_connection()

    end_time = datetime.now()

    if argv!='':
        record_runtime(start_time, end_time)


if __name__ == "__main__":
    main()
