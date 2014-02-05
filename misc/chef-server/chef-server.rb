nginx['non_ssl_port'] = 8080
nginx['enable_non_ssl'] = true
nginx['ssl_port'] = 443
nginx['url'] = "https://#{node['fqdn']}"
