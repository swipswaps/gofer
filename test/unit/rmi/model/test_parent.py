from unittest import TestCase

from mock import call, patch, Mock

from gofer.rmi.model import protocol
from gofer.rmi.model.parent import Monitor, Call
from gofer.rmi.model.parent import Result, Progress, Error, Raised


MODULE = 'gofer.rmi.model.parent'


class TestMonitor(TestCase):

    @patch(MODULE + '.sleep')
    def test_run(self, sleep):
        context = Mock()
        context.cancelled.side_effect = [False, True]
        child = Mock()
        pipe = Mock()

        # test
        m = Monitor(context, child, pipe)
        m.run()

        # validation
        pipe.send.assert_called_once_with(0)
        child.terminate.assert_called_once_with()
        sleep.assert_called_once_with(0.10)

    @patch(MODULE + '.Monitor.join')
    def test_stop(self, join):
        context = Mock()
        child = Mock()
        pipe = Mock()

        # test
        m = Monitor(context, child, pipe)
        m.stop()

        # validation
        self.assertEqual(m.poll, False)
        join.assert_called_once_with()


class TestReplies(TestCase):

    def test_result(self):
        payload = 'done'
        reply = Result(payload)

        # test
        try:
            reply()
            self.fail(msg='End not raised')
        except protocol.End, end:
            self.assertEqual(end.result, payload)

    @patch(MODULE + '.Context.current')
    def test_progress(self, current):
        class P(object):
            report = Mock()
        context = Mock()
        context.progress = P()
        current.return_value = context
        payload = protocol.ProgressPayload(1, 2, 3)
        reply = Progress(payload)

        # test
        reply()

        context.progress.report.assert_called_once_with()
        self.assertEqual(context.progress.__dict__, payload.__dict__)

    def test_error(self):
        payload = 18
        reply = Error(payload)
        self.assertRaises(Exception, reply)

    def test_raised(self):
        payload = ValueError()

        # test
        reply = Raised(payload)
        try:
            reply()
            self.fail(msg='ValueError not raised')
        except ValueError, e:
            self.assertEqual(e, payload)


class TestCall(TestCase):

    @patch(MODULE + '.Call.read')
    @patch(MODULE + '.Target')
    @patch(MODULE + '.Context')
    @patch(MODULE + '.Process')
    @patch(MODULE + '.Pipe')
    @patch(MODULE + '.Monitor')
    def test_call(self, monitor, pipe, process, context, target, read):
        inbound = Mock()
        outbound = Mock()
        pipe.return_value = inbound, outbound

        # test
        _call = Call(Mock(), 1, 2, a=1, b=2)
        _call()

        # validation
        pipe.assert_called_once_with()
        target.assert_called_once_with(_call.method, *_call.args, **_call.kwargs)
        process.assert_called_once_with(target=target.return_value, args=(outbound,))
        monitor.assert_called_once_with(
                context.current.return_value, process.return_value, outbound)
        monitor.return_value.start.assert_called_once_with()
        read.assert_called_once_with(inbound)
        monitor.return_value.stop.assert_called_once_with()
        process.return_value.join.assert_called_once_with()

    @patch(MODULE + '.protocol.Reply')
    def test_read(self, reply):
        replies = [Mock(), Mock(side_effect=protocol.End(18))]
        reply.read.side_effect = replies
        _call = Call(Mock())
        pipe = Mock()

        # test
        retval = _call.read(pipe)

        # validation
        self.assertEqual(
            reply.read.call_args_list,
            [
                call(pipe),
                call(pipe)
            ])
        self.assertEqual(retval, 18)
