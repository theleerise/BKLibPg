from BKLibPg.manager.manager_builder import ManagerBuilder
from BKLibPg.model import Model
from BKLibPg.data_types import (
    IntegerType, StringType, FloatType, BooleanType,
    DateTimeType, InetType
)

##################################################################################
###                                   MODEL                                    ###
##################################################################################
class ModelActivityConnections(Model):
    fields = {
        "pid": IntegerType("pid", primary_key=True, doc="ID del proceso"),
        "leader_pid": IntegerType("leader_pid", nullable=True),
        "backend_type": StringType("backend_type", nullable=True),
        "application_name": StringType("application_name", nullable=True),
        "state": StringType("state", nullable=True),
        "state_change": DateTimeType("state_change", nullable=True),
        "backend_start": DateTimeType("backend_start", nullable=True),
        "xact_start": DateTimeType("xact_start", nullable=True),
        "query_start": DateTimeType("query_start", nullable=True),
        "query_duration": FloatType("query_duration", nullable=True),

        "usesysid": IntegerType("usesysid", nullable=True),
        "username": StringType("username", nullable=True),
        "datid": IntegerType("datid", nullable=True),
        "database_name": StringType("database_name", nullable=True),

        "client_addr": InetType("client_addr", nullable=True),
        "client_hostname": StringType("client_hostname", nullable=True),
        "client_port": IntegerType("client_port", nullable=True),

        "wait_event_type": StringType("wait_event_type", nullable=True),
        "wait_event": StringType("wait_event", nullable=True),
        "backend_xid": IntegerType("backend_xid", nullable=True),
        "backend_xmin": IntegerType("backend_xmin", nullable=True),

        "query_id": FloatType("query_id", nullable=True),
        "query": StringType("query", nullable=True),

        "locktype": StringType("locktype", nullable=True),
        "lock_mode": StringType("lock_mode", nullable=True),
        "lock_granted": BooleanType("lock_granted", nullable=True),
        "lock_table": StringType("lock_table", nullable=True),

        "calls": IntegerType("calls", nullable=True),
        "total_exec_time": FloatType("total_exec_time", nullable=True),
        "mean_exec_time": FloatType("mean_exec_time", nullable=True),
        "rows": IntegerType("rows", nullable=True),

        "shared_blks_hit": IntegerType("shared_blks_hit", nullable=True),
        "shared_blks_read": IntegerType("shared_blks_read", nullable=True),
        "shared_blks_written": IntegerType("shared_blks_written", nullable=True),
        "temp_blks_read": IntegerType("temp_blks_read", nullable=True),
        "temp_blks_written": IntegerType("temp_blks_written", nullable=True),

        "wal_records": IntegerType("wal_records", nullable=True),
        "wal_bytes": FloatType("wal_bytes", nullable=True),
    }


##################################################################################
###                                  MANAGER                                   ###
##################################################################################
class MgrdbActivityConnections(ManagerBuilder):
    """
    Manager for database activity connections.
    This class is responsible for managing the connections to the database
    and providing methods to interact with them.
    """
    def __init__(self, connection_engine, input_model=ModelActivityConnections, output_model=ModelActivityConnections, table_name=None, id=None):
        """
        Initializes the MgrdbActivityConnections manager.

        :param connection_engine: The engine used to connect to the database.
        :param input_model: The model for input data.
        :param output_model: The model for output data.
        """
        super().__init__(connection_engine, input_model, output_model, table_name, id)

    def _get_sql_query(self):
        sql = f"""
            SELECT
                  A.PID
                , A.LEADER_PID
                , A.BACKEND_TYPE
                , A.APPLICATION_NAME
                , A.STATE
                , A.STATE_CHANGE
                , A.BACKEND_START
                , A.XACT_START
                , A.QUERY_START
                , EXTRACT(EPOCH FROM NOW() - A.QUERY_START) AS QUERY_DURATION
                -- USUARIO Y BASE DE DATOS
                , A.USESYSID
                , R.ROLNAME AS USERNAME
                , A.DATID
                , D.DATNAME AS DATABASE_NAME
                -- CONEXIÓN CLIENTE
                , A.CLIENT_ADDR
                , A.CLIENT_HOSTNAME
                , A.CLIENT_PORT
                -- INFORMACIÓN DE ESPERA Y TRANSACCIONES
                , A.WAIT_EVENT_TYPE
                , A.WAIT_EVENT
                , A.BACKEND_XID
                , A.BACKEND_XMIN
                -- CONSULTA ACTUAL
                , A.QUERY_ID
                , A.QUERY
                -- LOCKS
                , L.LOCKTYPE
                , L.MODE AS LOCK_MODE
                , L.GRANTED AS LOCK_GRANTED
                , L.RELATION::REGCLASS AS LOCK_TABLE
                -- ESTADÍSTICAS DEL STATEMENT
                , S.CALLS
                , S.TOTAL_EXEC_TIME
                , S.MEAN_EXEC_TIME
                , S.ROWS
                , S.SHARED_BLKS_HIT
                , S.SHARED_BLKS_READ
                , S.SHARED_BLKS_WRITTEN
                , S.TEMP_BLKS_READ
                , S.TEMP_BLKS_WRITTEN
                , S.WAL_RECORDS
                , S.WAL_BYTES
            FROM PG_STAT_ACTIVITY A
            LEFT JOIN PG_ROLES R
                ON A.USESYSID = R.OID
            LEFT JOIN PG_DATABASE D
                ON A.DATID = D.OID
            LEFT JOIN PG_LOCKS L
                ON A.PID = L.PID
            LEFT JOIN PG_STAT_STATEMENTS S
                ON A.QUERY_ID = S.QUERYID
        """
        return sql


