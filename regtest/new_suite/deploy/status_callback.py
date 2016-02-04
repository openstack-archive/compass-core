import httplib
import json
import sys
import logging

def task_error(host, data):
    logging.info("task_error: host=%s,data=%s" % (host, data))

    if type(data) == dict:
        invocation = data.pop('invocation', {})

    notify_host("localhost", host, "failed")

class CallbackModule(object):
    """
    logs playbook results, per host, in /var/log/ansible/hosts
    """

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        task_error(host, res)

    def runner_on_ok(self, host, res):
        pass

    def runner_on_skipped(self, host, item=None):
        pass

    def runner_on_unreachable(self, host, res):
        pass

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        task_error(host, res)

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, name):
        pass

    def playbook_on_stats(self, stats):
        logging.info("playbook_on_stats enter")
        hosts = sorted(stats.processed.keys())
        host_vars = self.playbook.inventory.get_variables(hosts[0])
        cluster_name = host_vars['cluster_name']
        failures = False
        unreachable = False

        for host in hosts:
            summary = stats.summarize(host)

            if summary['failures'] > 0:
                failures = True
            if summary['unreachable'] > 0:
                unreachable = True

        if failures or unreachable:
            for host in hosts:
                notify_host("localhost", host, "error")
            return

        for host in hosts:
            clusterhost_name = host + "." + cluster_name
            notify_host("localhost", clusterhost_name, "succ")


def raise_for_status(resp):
    if resp.status < 200 or resp.status > 300:
        raise RuntimeError("%s, %s, %s" % (resp.status, resp.reason, resp.read()))

def auth(conn):
    credential = {}
    credential['email'] = "admin@huawei.com"
    credential['password'] = "admin"
    url = "/api/users/token"
    headers = {"Content-type": "application/json",
               "Accept": "*/*"}
    conn.request("POST", url, json.dumps(credential), headers)
    resp = conn.getresponse()

    raise_for_status(resp)
    return json.loads(resp.read())["token"]

def notify_host(compass_host, host, status):
    if status == "succ":
        body = {"ready": True}
        url = "/api/clusterhosts/%s/state_internal" % host
    elif status == "error":
        body = {"state": "ERROR"}
        host = host.strip("host")
        url = "/api/clusterhosts/%s/state" % host
    else:
        logging.error("notify_host: host %s with status %s is not supported" \
                % (host, status))
        return

    headers = {"Content-type": "application/json",
               "Accept": "*/*"}

    conn = httplib.HTTPConnection(compass_host, 80)
    token = auth(conn)
    headers["X-Auth-Token"] = token
    logging.info("host=%s,url=%s,body=%s,headers=%s" % (compass_host,url,json.dumps(body),headers))
    conn.request("POST", url, json.dumps(body), headers)
    resp = conn.getresponse()
    try:
        raise_for_status(resp)
        logging.info("notify host status success!!! status=%s, body=%s" % (resp.status, resp.read()))
    except Exception as e:
        logging.error("http request failed %s" % str(e))
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.error("params: host, status is need")
        sys.exit(1)

    host = sys.argv[1]
    status = sys.argv[2]
    notify_host(host, status)
