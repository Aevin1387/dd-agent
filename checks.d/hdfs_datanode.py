'''
HDFS DataNode Metrics
---------------------
hdfs_datanode.dfs_remaining                  The remaining disk space left in bytes
hdfs_datanode.dfs_capacity                   Disk capacity in bytes
hdfs_datanode.dfs_used                       Disk usage in bytes
hdfs_datanode.cache_capacity                 Cache capacity in bytes
hdfs_datanode.cache_used                     Cache used in bytes
hdfs_datanode.num_failed_volumes             Number of failed volumes
hdfs_datanode.last_volume_failure_date       Date the last volume failed
hdfs_datanode.estimated_capacity_lost_total  The estimated capacity lost in bytes
hdfs_datanode.num_blocks_cached              The number of blocks cached
hdfs_datanode.num_blocks_failed_to_cache     The number of blocks that failed to cache
hdfs_datanode.num_blocks_failed_to_uncache   The number of failed blocks to remove from cache
'''

# stdlib
from urlparse import urljoin

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError

# Project
from checks import AgentCheck

# Service check names
JMX_SERVICE_CHECK = 'hdfs_datanode.jmx.can_connect'

# URL Paths
JMX_PATH = 'jmx'

# Metric types
GAUGE = 'gauge'

# HDFS bean name
HDFS_DATANODE_BEAN_NAME = 'Hadoop:service=DataNode,name=FSDatasetState'

# HDFS metrics
HDFS_METRICS = {
    'Remaining' : ('hdfs_datanode.dfs_remaining',  GAUGE),
    'Capacity' :('hdfs_datanode.dfs_capacity', GAUGE),
    'DfsUsed' : ('hdfs_datanode.dfs_used', GAUGE),
    'CacheCapacity' : ('hdfs_datanode.cache_capacity', GAUGE),
    'CacheUsed' : ('hdfs_datanode.cache_used', GAUGE),
    'NumFailedVolumes' : ('hdfs_datanode.num_failed_volumes', GAUGE),
    'LastVolumeFailureDate' : ('hdfs_datanode.last_volume_failure_date', GAUGE),
    'EstimatedCapacityLostTotal' : ('hdfs_datanode.estimated_capacity_lost_total', GAUGE),
    'NumBlocksCached' : ('hdfs_datanode.num_blocks_cached', GAUGE),
    'NumBlocksFailedToCache' : ('hdfs_datanode.num_blocks_failed_to_cache', GAUGE),
    'NumBlocksFailedToUnCache' : ('hdfs_datanode.num_blocks_failed_to_uncache', GAUGE)
}

class HDFSDataNode(AgentCheck):

    def check(self, instance):
        jmx_address = instance.get('hdfs_datanode_jmx_uri')
        if jmx_address is None:
            raise Exception('The JMX URL must be specified in the instance configuration')

        # Get metrics from JMX
        self._hdfs_datanode_metrics(jmx_address)

    def _hdfs_datanode_metrics(self, jmx_uri):
        '''
        Get HDFS data node metrics from JMX
        '''
        response = self._rest_request_to_json(jmx_uri,
            JMX_PATH,
            query_params={'qry':HDFS_DATANODE_BEAN_NAME})

        beans = response.get('beans', [])

        tags = ['datanode_url:' + jmx_uri]

        if beans:

            bean = next(iter(beans))
            bean_name = bean.get('name')

            if bean_name != HDFS_DATANODE_BEAN_NAME:
                raise Exception("Unexpected bean name {0}".format(bean_name))

            for metric, (metric_name, metric_type) in HDFS_METRICS.iteritems():
                metric_value = bean.get(metric)

                if metric_value is not None:
                    self._set_metric(metric_name, metric_type, metric_value, tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None):
        '''
        Set a metric
        '''
        if metric_type == GAUGE:
            self.gauge(metric_name, value, tags=tags)
        else:
            self.log.error('Metric type "%s" unknown' % (metric_type))

    def _rest_request_to_json(self, address, object_path, query_params):
        '''
        Query the given URL and return the JSON response
        '''
        response_json = None

        service_check_tags = ['datanode_url:' + address]

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add query_params as arguments
        if query_params:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in query_params.iteritems()])
            url = urljoin(url, '?' + query)

        self.log.debug('Attempting to connect to "%s"' % url)

        try:
            response = requests.get(url)
            response.raise_for_status()
            response_json = response.json()

        except Timeout as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request timeout: {0}, {1}".format(url, e))
            raise

        except (HTTPError,
                InvalidURL,
                ConnectionError) as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request failed: {0}, {1}".format(url, e))
            raise

        except JSONDecodeError as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='JSON Parse failed: {0}, {1}'.format(url, e))
            raise

        except ValueError as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message=e)
            raise

        else:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.OK,
                tags=service_check_tags,
                message='Connection to %s was successful' % url)

        return response_json


    def _join_url_dir(self, url, *args):
        '''
        Join a URL with multiple directories
        '''

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url
