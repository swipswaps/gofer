#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

from threading import local as Local
from logging import getLogger

from uuid import uuid4

from gofer import Singleton
from gofer.messaging.adapter.url import URL
from gofer.messaging.adapter.factory import Adapter

# routing key
ROUTE_ALL = '#'

# exchange types
DIRECT = 'direct'
TOPIC = 'topic'

DEFAULT_URL = 'amqp://localhost'


log = getLogger(__name__)


class Destination(object):
    """
    An AMQP destination.
    :ivar routing_key: Message routing key.
    :type routing_key: str
    :ivar exchange: An (optional) AMQP exchange.
    :type exchange: str
    """

    ROUTING_KEY = 'routing_key'
    EXCHANGE = 'exchange'

    @staticmethod
    def create(d):
        return Destination(d[Destination.ROUTING_KEY], d[Destination.EXCHANGE])

    def __init__(self, routing_key, exchange=''):
        """
        :param exchange: An AMQP exchange.
        :type exchange: str
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        self.routing_key = routing_key
        self.exchange = exchange

    def dict(self):
        return {
            Destination.ROUTING_KEY: self.routing_key,
            Destination.EXCHANGE: self.exchange,
        }

    def __eq__(self, other):
        return isinstance(other, Destination) and \
            self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)


# --- node -------------------------------------------------------------------


class Node(object):
    """
    An AMQP node.
    :ivar name: The node name.
    :type name: str
    """

    def __init__(self, name):
        """
        :param name: The node name.
        :type name: str
        """
        self.name = name

    def declare(self, url):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        :return: self
        """
        raise NotImplementedError()

    def delete(self, url):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        :return: self
        """
        raise NotImplementedError()


class BaseExchange(Node):
    """
    An AMQP exchange.
    :ivar policy: The routing policy (direct|topic|..).
    :type policy: str
    :ivar durable: Indicates the exchange is durable.
    :type durable: bool
    :ivar auto_delete: The exchange is auto deleted.
    :type auto_delete: bool
    """

    def __init__(self, name, policy=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        """
        Node.__init__(self, name)
        self.policy = policy
        self.durable = True
        self.auto_delete = False

    def __eq__(self, other):
        return isinstance(other, BaseExchange) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Exchange(BaseExchange):

    def __init__(self, name, policy=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        """
        BaseExchange.__init__(self, name, policy)

    def declare(self, url=DEFAULT_URL):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        """
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name, policy=self.policy)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.declare(url)

    def delete(self, url=DEFAULT_URL):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        """
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name)
        impl.delete(url)


class BaseQueue(Node):
    """
    An AMQP queue.
    :ivar exchange: An AMQP exchange.
    :type exchange: Exchange
    :ivar routing_key: Message routing key.
    :type routing_key: str
    :ivar durable: Indicates the queue is durable.
    :type durable: bool
    :ivar auto_delete: The queue is auto deleted.
    :type auto_delete: bool
    :ivar exclusive: Indicates the queue can only have one consumer.
    :type exclusive: bool
    """

    def __init__(self, name, exchange, routing_key):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: BaseExchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        Node.__init__(self, name)
        self.exchange = exchange
        self.routing_key = routing_key
        self.durable = True
        self.auto_delete = False
        self.exclusive = False

    def destination(self, url):
        """
        Get a destination object for the node.
        :param url: The broker URL.
        :type url: str
        :return: A destination for the node.
        :rtype: Destination
        """
        raise NotImplementedError()

    def __eq__(self, other):
        return isinstance(other, BaseQueue) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Queue(BaseQueue):

    def __init__(self, name, exchange=None, routing_key=None):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: BaseExchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        BaseQueue.__init__(self, name, exchange, routing_key)

    def declare(self, url=DEFAULT_URL):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        :return: self
        """
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name, self.exchange, self.routing_key)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.exclusive = self.exclusive
        impl.declare(url)

    def delete(self, url=None):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        :return: self
        """
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name)
        impl.delete(url)
        
    def destination(self, url):
        """
        Get a destination object for the node.
        :param url: The broker URL.
        :type url: str
        :return: A destination for the node.
        :rtype: Destination
        """
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name, self.exchange, self.routing_key)
        return impl.destination(url)


# --- endpoint ---------------------------------------------------------------


class BaseEndpoint(object):
    """
    Base class for an AMQP endpoint.
    :ivar url: The broker URL.
    :type url: str
    :ivar uuid: The endpoint UUID.
    :type uuid: str
    :ivar authenticator: A message authenticator.
    :type authenticator: gofer.messaging.auth.Authenticator
    """

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        self.url = url
        self.uuid = str(uuid4())
        self.authenticator = None

    def id(self):
        """
        Get the endpoint id
        :return: The id.
        :rtype: str
        """
        return self.uuid

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        raise NotImplementedError()

    def open(self):
        """
        Open and configure the endpoint.
        """
        raise NotImplementedError()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        raise NotImplementedError()

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        raise NotImplementedError()

    def close(self):
        """
        Close the endpoint.
        """
        raise NotImplementedError()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


# --- messenger --------------------------------------------------------------


class Messenger(BaseEndpoint):
    """
    Provides AMQP messaging.
    """

    def endpoint(self):
        """
        Get the messenger endpoint.
        :return: An endpoint object.
        :rtype: BaseEndpoint
        """
        raise NotImplementedError()

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        return self.endpoint().channel()

    def open(self):
        """
        Open and configure the endpoint.
        """
        self.endpoint().open()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        self.endpoint().ack(message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self.endpoint().reject(message, requeue)

    def close(self):
        """
        Close the endpoint.
        """
        self.endpoint().close()


# --- reader -----------------------------------------------------------------


class BaseReader(Messenger):
    """
    An AMQP message reader.
    """

    def __init__(self, queue, url):
        """
        :param queue: The queue to consumer.
        :type queue: gofer.messaging.adapter.model.BaseQueue
        :param url: The broker url.
        :type url: str
        """
        Messenger.__init__(self, url)
        self.queue = queue

    def get(self, timeout=None):
        """
        Get the next message.
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next message, or (None).
        """
        raise NotImplementedError()

    def next(self, timeout=90):
        """
        Get the next document from the queue.
        :param timeout: The read timeout.
        :type timeout: int
        :return: A tuple of: (document, ack())
        :rtype: (Document, callable)
        :raises: model.InvalidDocument
        """
        raise NotImplementedError()

    def search(self, sn, timeout=90):
        """
        Search the reply queue for the document with the matching serial #.
        :param sn: The expected serial number.
        :type sn: str
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next document.
        :rtype: Document
        """
        raise NotImplementedError()


class Reader(BaseReader):
    """
    An AMQP message reader.
    """

    def __init__(self, queue, url=DEFAULT_URL):
        """
        :param queue: The queue to consumer.
        :type queue: gofer.messaging.adapter.model.BaseQueue
        :param url: The broker url.
        :type url: str
        :see: gofer.messaging.adapter.url.URL
        """
        BaseReader.__init__(self, queue, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Reader(queue, url)

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        return self._impl.channel()

    def open(self):
        """
        Open the reader.
        """
        self._impl.open()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        self._impl.ack(message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self._impl.reject(message, requeue)

    def close(self):
        """
        Close the reader.
        """
        self._impl.close()

    def get(self, timeout=None):
        """
        Get the next message.
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next message, or (None).
        """
        return self._impl.get(timeout)

    def next(self, timeout=90):
        """
        Get the next document from the queue.
        :param timeout: The read timeout.
        :type timeout: int
        :return: A tuple of: (document, ack())
        :rtype: (Document, callable)
        :raises: model.InvalidDocument
        """
        self._impl.authenticator = self.authenticator
        return self._impl.next(timeout)

    def search(self, sn, timeout=90):
        """
        Search the reply queue for the document with the matching serial #.
        :param sn: The expected serial number.
        :type sn: str
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next document.
        :rtype: Document
        """
        log.debug('searching for: sn=%s', sn)
        while True:
            document, ack = self.next(timeout)
            if document:
                ack()
            else:
                return
            if sn == document.sn:
                log.debug('search found: %s', document)
                return document
            else:
                log.debug('search discarding: %s', document)


# --- producer ---------------------------------------------------------------


class BaseProducer(Messenger):
    """
    An AMQP (message producer.
    """

    def send(self, destination, ttl, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.messaging.adapter.model.Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        """
        raise NotImplementedError()

    def broadcast(self, destinations, ttl, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.messaging.adapter.node.Node,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (addr,sn).
        :rtype: list
        """
        raise NotImplementedError()


class Producer(BaseProducer):
    """
    An AMQP (message producer.
    """

    def __init__(self, url=DEFAULT_URL):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseProducer.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Producer(url)

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        return self._impl.channel()

    def open(self):
        """
        Open the producer.
        """
        self._impl.open()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        self._impl.ack(message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self._impl.reject(message, requeue)

    def close(self):
        """
        Close the producer.
        """
        self._impl.close()

    def send(self, destination, ttl=None, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.messaging.adapter.model.Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        """
        self._impl.authenticator = self.authenticator
        return self._impl.send(destination, ttl, **body)

    def broadcast(self, destinations, ttl=None, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.messaging.adapter.node.Node,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (addr,sn).
        :rtype: list
        """
        self._impl.authenticator = self.authenticator
        return self._impl.broadcast(destinations, ttl, **body)


class BasePlainProducer(Messenger):
    """
    An plain AMQP message producer.
    """

    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.messaging.adapter.model.Destination
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        raise NotImplementedError()

    def broadcast(self, destinations, content, ttl=None):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.messaging.adapter.node.Node,..]
        :param content: The message content
        :type content: buf
        """
        raise NotImplementedError()


class PlainProducer(BasePlainProducer):
    """
    An plain AMQP message producer.
    """

    def __init__(self, url=DEFAULT_URL):
        """
        :param url: The broker url <adapter>://<user>:<pass>@<host>:<port>/<virtual-host>.
        :type url: str
        """
        BasePlainProducer.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.PlainProducer(url)

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        return self._impl.channel()

    def open(self):
        """
        Open the producer.
        """
        self._impl.open()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        self._impl.ack(message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self._impl.reject(message, requeue)

    def close(self):
        """
        Close the producer.
        """
        self._impl.close()

    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.messaging.adapter.model.Destination
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        self._impl.authenticator = self.authenticator
        return self._impl.send(destination, content, ttl)

    def broadcast(self, destinations, content, ttl=None):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.messaging.adapter.node.Node,..]
        :param content: The message content
        :type content: buf
        """
        self._impl.authenticator = self.authenticator
        return self._impl.broadcast(destinations, content, ttl)


# --- broker -----------------------------------------------------------------


class BrokerSingleton(Singleton):
    """
    Broker MetaClass.
    Singleton by simple url.
    """

    @staticmethod
    def key(t, d):
        url = t[0]
        if isinstance(url, (str, URL)):
            return str(url)
        else:
            raise ValueError('url must be: str|URL')

    def __call__(cls, *args, **kwargs):
        if not args:
            args = (DEFAULT_URL,)
        return Singleton.__call__(cls, *args, **kwargs)


class BaseBroker(object):
    """
    Represents an AMQP broker.
    :ivar connection: A thread local containing an open connection.
    :type connection: Local
    :ivar url: The broker's url.
    :type url: URL
    :ivar cacert: Path to a PEM encoded file containing
        the CA certificate used to validate the server certificate.
    :type cacert: str
    :ivar clientkey: Path to a PEM encoded file containing
        the private key used for client authentication.
    :type clientkey: str
    :ivar clientcert: Path to a PEM encoded file containing
        the certificate used for client authentication.  This file may also contain the
        PEM encoded private key.
    :type clientcert: str
    :ivar host_validation: Enable SSL host validation.
    :type host_validation: bool
    """

    __metaclass__ = BrokerSingleton

    def __init__(self, url):
        """
        :param url: The broker url:
            <adapter>+<scheme>://<userid:password@<host>:<port>/<virtual-host>.
        :type url: str|URL
        """
        if not isinstance(url, URL):
            url = URL(url)
        self.url = url
        self.connection = Local()
        self.cacert = None
        self.clientkey = None
        self.clientcert = None
        self.host_validation = False

    def connect(self):
        """
        Connect to the broker.
        :return: The AMQP connection object.
        """
        raise NotImplementedError()

    def close(self):
        """
        Close the connection to the broker.
        """
        raise NotImplementedError()

    @property
    def id(self):
        """
        Get the broker identity.
        :return: The broker ID which is defined by the URL.
        :rtype: str
        """
        return self.url.simple()

    @property
    def adapter(self):
        """
        Get the (gofer) adapter component of the url.
        :return: The adapter component.
        :rtype: str
        """
        return self.url.adapter

    @property
    def scheme(self):
        """
        Get the scheme component of the url.
        :return: The scheme component.
        :rtype: str
        """
        return self.url.scheme

    @property
    def host(self):
        """
        Get the host component of the url.
        :return: The host component.
        :rtype: str
        """
        return self.url.host

    @property
    def port(self):
        """
        Get the port component of the url.
        :return: The port component.
        :rtype: str
        """
        return self.url.port

    @property
    def userid(self):
        """
        Get the userid component of the url.
        :return: The userid component.
        :rtype: str
        """
        return self.url.userid

    @property
    def password(self):
        """
        Get the password component of the url.
        :return: The password component.
        :rtype: str
        """
        return self.url.password

    @property
    def virtual_host(self):
        """
        Get the virtual_host component of the url.
        :return: The virtual_host component.
        :rtype: str
        """
        return self.url.path

    def __str__(self):
        s = list()
        s.append('url=%s' % self.url)
        s.append('cacert=%s' % self.cacert)
        s.append('clientkey=%s' % self.clientkey)
        s.append('clientcert=%s' % self.clientcert)
        s.append('host-validation=%s' % self.host_validation)
        return '|'.join(s)


class Broker(BaseBroker):
    """
    Represents an AMQP broker.
    """

    def __init__(self, url=DEFAULT_URL):
        """
        :param url: The broker url:
            <adapter>+<scheme>://<userid:password@<host>:<port>/<virtual-host>.
        :type url: str|URL
        """
        BaseBroker.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Broker(url)

    def connect(self):
        """
        Connect to the broker.
        """
        self._impl.cacert = self.cacert
        self._impl.clientkey = self.clientkey
        self._impl.clientcert = self.clientcert
        self._impl.host_validation = self.host_validation
        self._impl.connect()

    def close(self):
        """
        Close the connection to the broker.
        """
        self._impl.close()
        
        
# --- ACK --------------------------------------------------------------------


class Ack:

    def __init__(self, endpoint, message):
        self.endpoint = endpoint
        self.message = message

    def accept(self):
        self.endpoint.ack(self.message)

    def reject(self, requeue=True):
        self.endpoint.reject(self.message, requeue)

    def __call__(self):
        self.accept()