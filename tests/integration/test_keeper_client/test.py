import pytest
from helpers.client import CommandRequest
from helpers.cluster import ClickHouseCluster
from helpers.test_tools import TSV


cluster = ClickHouseCluster(__file__)

node = cluster.add_instance(
    "node",
    main_configs=["configs/keeper_config.xml"],
    with_zookeeper=True,
    stay_alive=True,
)


@pytest.fixture(scope="module", autouse=True)
def started_cluster():
    try:
        cluster.start()
        yield cluster

    finally:
        cluster.shutdown()


def keeper_query(query: str):
    return CommandRequest(
        [
            cluster.server_bin_path,
            "keeper-client",
            "--host",
            str(cluster.get_instance_ip("zoo1")),
            "--port",
            str(cluster.zookeeper_port),
            "-q",
            query,
        ],
        stdin="",
    )


def test_big_family():
    command = keeper_query(
        "create test_big_family foo;"
        "create test_big_family/1 foo;"
        "create test_big_family/1/1 foo;"
        "create test_big_family/1/2 foo;"
        "create test_big_family/1/3 foo;"
        "create test_big_family/1/4 foo;"
        "create test_big_family/1/5 foo;"
        "create test_big_family/2 foo;"
        "create test_big_family/2/1 foo;"
        "create test_big_family/2/2 foo;"
        "create test_big_family/2/3 foo;"
        "find_big_family test_big_family;"
    )

    assert command.get_answer() == TSV(
        [
            ["/test_big_family/1", "5"],
            ["/test_big_family/2", "3"],
            ["/test_big_family/2/3", "0"],
            ["/test_big_family/2/2", "0"],
            ["/test_big_family/2/1", "0"],
            ["/test_big_family/1/5", "0"],
            ["/test_big_family/1/4", "0"],
            ["/test_big_family/1/3", "0"],
            ["/test_big_family/1/2", "0"],
            ["/test_big_family/1/1", "0"],
        ]
    )

    command = keeper_query("find_big_family test_big_family 1;")

    assert command.get_answer() == TSV(
        [
            ["/test_big_family/1", "5"],
        ]
    )


def test_find_super_nodes():
    command = keeper_query(
        "create test_find_super_nodes foo;"
        "create test_find_super_nodes/1 foo;"
        "create test_find_super_nodes/1/1 foo;"
        "create test_find_super_nodes/1/2 foo;"
        "create test_find_super_nodes/1/3 foo;"
        "create test_find_super_nodes/1/4 foo;"
        "create test_find_super_nodes/1/5 foo;"
        "create test_find_super_nodes/2 foo;"
        "create test_find_super_nodes/2/1 foo;"
        "create test_find_super_nodes/2/2 foo;"
        "create test_find_super_nodes/2/3 foo;"
        "create test_find_super_nodes/2/4 foo;"
        "cd test_find_super_nodes;"
        "find_super_nodes 4;"
    )

    assert command.get_answer() == TSV(
        [
            ["/test_find_super_nodes/1", "5"],
            ["/test_find_super_nodes/2", "4"],
        ]
    )


def test_delete_stable_backups():
    command = keeper_query(
        "create /clickhouse/backups foo;"
        "create /clickhouse/backups/1 foo;"
        "create /clickhouse/backups/1/stage foo;"
        "create /clickhouse/backups/1/stage/alive123 foo;"
        "create /clickhouse/backups/2 foo;"
        "create /clickhouse/backups/2/stage foo;"
        "create /clickhouse/backups/2/stage/dead123 foo;"
        "delete_stable_backups;"
        "y;"
        "ls clickhouse/backups;"
    )

    assert command.get_answer() == (
        "You are going to delete all inactive backups in /clickhouse/backups. Continue?\n"
        'Found backup "/clickhouse/backups/1", checking if it\'s active\n'
        'Backup "/clickhouse/backups/1" is active, not going to delete\n'
        'Found backup "/clickhouse/backups/2", checking if it\'s active\n'
        'Backup "/clickhouse/backups/2" is not active, deleting it\n'
        "1\n"
    )


def test_base_commands():
    command = keeper_query(
        "create test_create_zk_node1 testvalue1;"
        "create test_create_zk_node_2 testvalue2;"
        "get test_create_zk_node1;"
    )

    assert command.get_answer() == "testvalue1\n"


def test_four_letter_word_commands():
    command = keeper_query("ruok")
    assert command.get_answer() == "imok\n"
