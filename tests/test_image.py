from iterators import TimeoutIterator
import pytest
import re
import signal
import testinfra
import time
from datetime import datetime

from helpers import get_app_home, get_app_install_dir, get_bootstrap_proc, \
    parse_properties, parse_xml, run_image, \
    wait_for_http_response, wait_for_proc, wait_for_state, wait_for_log

PORT = 8095
STATUS_URL = f'http://localhost:{PORT}/status'


def test_server_xml_defaults(docker_cli, image):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/apache-tomcat/conf/server.xml')
    connector = xml.find('.//Connector')

    assert connector.get('port') == '8095'
    assert connector.get('maxThreads') == '150'
    assert connector.get('minSpareThreads') == '25'
    assert connector.get('connectionTimeout') == '20000'
    assert connector.get('enableLookups') == 'false'
    assert connector.get('protocol') == 'HTTP/1.1'
    assert connector.get('acceptCount') == '100'
    assert connector.get('secure') == 'false'
    assert connector.get('scheme') == 'http'
    assert connector.get('proxyName') == ''
    assert connector.get('proxyPort') == ''
    assert connector.get('maxHttpHeaderSize') == '8192'

def test_server_xml_access_log_enabled(docker_cli, image):
    environment = {
        'ATL_TOMCAT_ACCESS_LOG': 'true',
        'ATL_TOMCAT_PROXY_INTERNAL_IPS': '192.168.1.1',
    }

    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/apache-tomcat/conf/server.xml')
    remove_ip_value = xml.find('.//Engine/Valve[@className="org.apache.catalina.valves.RemoteIpValve"]')
    assert remove_ip_value.get('internalProxies') == environment.get('ATL_TOMCAT_PROXY_INTERNAL_IPS')
    access_log_valve = xml.find('.//Engine/Valve[@className="org.apache.catalina.valves.AccessLogValve"]')
    assert access_log_valve.get('prefix') == 'crowd_access'


def test_access_log_disabled(docker_cli, image):
    environment = {
        'ATL_TOMCAT_ACCESS_LOG': 'false',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))
    current_date = datetime.now().date()
    formatted_date = current_date.strftime("%Y-%m-%d")
    assert not container.file(f'{get_app_install_dir(container)}/apache-tomcat/logs/crowd_access.{formatted_date}.log').exists




def test_server_xml_params(docker_cli, image):
    environment = {
        'ATL_TOMCAT_MGMT_PORT': '8006',
        'ATL_TOMCAT_PORT': '9090',
        'ATL_TOMCAT_MAXTHREADS': '201',
        'ATL_TOMCAT_MINSPARETHREADS': '11',
        'ATL_TOMCAT_CONNECTIONTIMEOUT': '20001',
        'ATL_TOMCAT_ENABLELOOKUPS': 'true',
        'ATL_TOMCAT_PROTOCOL': 'org.apache.coyote.http11.Http11AprProtocol',
        'ATL_TOMCAT_ACCEPTCOUNT': '11',
        'ATL_TOMCAT_SECURE': 'true',
        'ATL_TOMCAT_SCHEME': 'https',
        'ATL_PROXY_NAME': 'crowd.atlassian.com',
        'ATL_PROXY_PORT': '443',
        'ATL_TOMCAT_MAXHTTPHEADERSIZE': '8193',
        'ATL_TOMCAT_CONTEXTPATH': '/mycrowd',
        "ATL_TOMCAT_ACCESS_LOG": 'true',
        'ATL_TOMCAT_ACCESS_LOGS_MAXDAYS': '10',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/apache-tomcat/conf/server.xml')
    connector = xml.find('.//Connector')
    context = xml.find('.//Context')
    valve = xml.find('.//Valve[@className="org.apache.catalina.valves.AccessLogValve"]')

    assert xml.get('port') == environment.get('ATL_TOMCAT_MGMT_PORT')

    assert connector.get('port') == environment.get('ATL_TOMCAT_PORT')
    assert connector.get('maxThreads') == environment.get('ATL_TOMCAT_MAXTHREADS')
    assert connector.get('minSpareThreads') == environment.get('ATL_TOMCAT_MINSPARETHREADS')
    assert connector.get('connectionTimeout') == environment.get('ATL_TOMCAT_CONNECTIONTIMEOUT')
    assert connector.get('enableLookups') == environment.get('ATL_TOMCAT_ENABLELOOKUPS')
    assert connector.get('protocol') == environment.get('ATL_TOMCAT_PROTOCOL')
    assert connector.get('acceptCount') == environment.get('ATL_TOMCAT_ACCEPTCOUNT')
    assert connector.get('secure') == environment.get('ATL_TOMCAT_SECURE')
    assert connector.get('scheme') == environment.get('ATL_TOMCAT_SCHEME')
    assert connector.get('proxyName') == environment.get('ATL_PROXY_NAME')
    assert connector.get('proxyPort') == environment.get('ATL_PROXY_PORT')
    assert connector.get('maxHttpHeaderSize') == environment.get('ATL_TOMCAT_MAXHTTPHEADERSIZE')

    # FIXME - Crowd context path is nontrivial to set
    # assert context.get('path') == environment.get('ATL_TOMCAT_CONTEXTPATH')

    assert valve.get('maxDays') == environment.get('ATL_TOMCAT_ACCESS_LOGS_MAXDAYS')


def test_server_xml_catalina_fallback(docker_cli, image):
    environment = {
        'CATALINA_CONNECTOR_PROXYNAME': 'crowd.atlassian.com',
        'CATALINA_CONNECTOR_PROXYPORT': '443',
        'CATALINA_CONNECTOR_SECURE': 'true',
        'CATALINA_CONNECTOR_SCHEME': 'https',
        'CATALINA_CONTEXT_PATH': '/mycrowd',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/apache-tomcat/conf/server.xml')
    connector = xml.find('.//Connector')
    context = xml.find('.//Context')

    assert connector.get('proxyName') == environment.get('CATALINA_CONNECTOR_PROXYNAME')
    assert connector.get('proxyPort') == environment.get('CATALINA_CONNECTOR_PROXYPORT')
    assert connector.get('secure') == environment.get('CATALINA_CONNECTOR_SECURE')
    assert connector.get('scheme') == environment.get('CATALINA_CONNECTOR_SCHEME')
    # FIXME - Crowd context path is nontrivial to set
    # assert context.get('path') == environment.get('CATALINA_CONTEXT_PATH')


def test_init_properties_custom_home(docker_cli, image, run_user):
    environment = {
        'CROWD_HOME': '/opt',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    properties = parse_properties(container,
                                  f'{get_app_install_dir(container)}/crowd-webapp/WEB-INF/classes/crowd-init.properties')
    assert properties.get('crowd.home') == environment['CROWD_HOME']


def test_init_properties_default_home(docker_cli, image, run_user):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    properties = parse_properties(container,
                                  f'{get_app_install_dir(container)}/crowd-webapp/WEB-INF/classes/crowd-init.properties')
    assert properties.get('crowd.home') == get_app_home(container)


def test_clean_shutdown(docker_cli, image, run_user):
    container = docker_cli.containers.run(image, detach=True, user=run_user, ports={PORT: PORT})
    host = testinfra.get_host("docker://" + container.id)

    started = r'org\.apache\.catalina\.startup\.Catalina\.start Server startup'
    wait_for_log(container, started)

    container.kill(signal.SIGTERM)

    end = r'org\.apache\.coyote\.AbstractProtocol\.destroy Destroying ProtocolHandler'
    wait_for_log(container, end)


def test_shutdown_script(docker_cli, image, run_user):
    container = docker_cli.containers.run(image, detach=True, user=run_user, ports={PORT: PORT})
    host = testinfra.get_host("docker://" + container.id)

    started = r'org\.apache\.catalina\.startup\.Catalina\.start Server startup'
    wait_for_log(container, started)

    container.exec_run('/shutdown-wait.sh')

    end = r'org\.apache\.coyote\.AbstractProtocol\.destroy Destroying ProtocolHandler'
    wait_for_log(container, end)
