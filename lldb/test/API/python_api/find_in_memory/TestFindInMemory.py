"""
Test Process::FindInMemory.
"""

import lldb
from lldbsuite.test.lldbtest import *
from lldbsuite.test import lldbutil
from address_ranges_helper import *


class FindInMemoryTestCase(TestBase):
    NO_DEBUG_INFO_TESTCASE = True

    def setUp(self):
        TestBase.setUp(self)

        self.build()
        (
            self.target,
            self.process,
            self.thread,
            self.bp,
        ) = lldbutil.run_to_source_breakpoint(
            self,
            "break here",
            lldb.SBFileSpec("main.cpp"),
        )
        self.assertTrue(self.bp.IsValid())

    def test_check_stack_pointer(self):
        """Make sure the 'stack_pointer' variable lives on the stack"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)

        frame = self.thread.GetSelectedFrame()
        ex = frame.EvaluateExpression("&stack_pointer")
        variable_region = lldb.SBMemoryRegionInfo()
        self.assertTrue(
            self.process.GetMemoryRegionInfo(
                ex.GetValueAsUnsigned(), variable_region
            ).Success(),
        )

        stack_region = lldb.SBMemoryRegionInfo()
        self.assertTrue(
            self.process.GetMemoryRegionInfo(frame.GetSP(), stack_region).Success(),
        )

        self.assertEqual(variable_region, stack_region)

    def test_find_in_memory_ok(self):
        """Make sure a match exists in the heap memory and the right address ranges are provided"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)
        error = lldb.SBError()
        addr = self.process.FindInMemory(
            SINGLE_INSTANCE_PATTERN_STACK,
            GetStackRange(self, True),
            1,
            error,
        )

        self.assertSuccess(error)
        self.assertNotEqual(addr, lldb.LLDB_INVALID_ADDRESS)

    def test_find_in_memory_double_instance_ok(self):
        """Make sure a match exists in the heap memory and the right address ranges are provided"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)
        error = lldb.SBError()
        addr = self.process.FindInMemory(
            DOUBLE_INSTANCE_PATTERN_HEAP,
            GetHeapRanges(self, True)[0],
            1,
            error,
        )

        self.assertSuccess(error)
        self.assertNotEqual(addr, lldb.LLDB_INVALID_ADDRESS)

    def test_find_in_memory_invalid_alignment(self):
        """Make sure the alignment 0 is failing"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)

        error = lldb.SBError()
        addr = self.process.FindInMemory(
            SINGLE_INSTANCE_PATTERN_STACK,
            GetStackRange(self, True),
            0,
            error,
        )

        self.assertFailure(error)
        self.assertEqual(addr, lldb.LLDB_INVALID_ADDRESS)

    def test_find_in_memory_invalid_address_range(self):
        """Make sure invalid address range is failing"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)

        error = lldb.SBError()
        addr = self.process.FindInMemory(
            SINGLE_INSTANCE_PATTERN_STACK,
            lldb.SBAddressRange(),
            1,
            error,
        )

        self.assertFailure(error)
        self.assertEqual(addr, lldb.LLDB_INVALID_ADDRESS)

    def test_find_in_memory_invalid_buffer(self):
        """Make sure the empty buffer is failing"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)

        error = lldb.SBError()
        addr = self.process.FindInMemory(
            "",
            GetStackRange(self, True),
            1,
            error,
        )

        self.assertFailure(error)
        self.assertEqual(addr, lldb.LLDB_INVALID_ADDRESS)

    def test_find_in_memory_unaligned(self):
        """Make sure the unaligned match exists in the heap memory and is not found with alignment 8"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)
        error = lldb.SBError()
        range = GetAlignedRange(self, True)

        # First we make sure the pattern is found with alignment 1
        addr = self.process.FindInMemory(
            UNALIGNED_INSTANCE_PATTERN_HEAP,
            range,
            1,
            error,
        )
        self.assertSuccess(error)
        self.assertNotEqual(addr, lldb.LLDB_INVALID_ADDRESS)

        # With alignment 8 the pattern should not be found
        addr = self.process.FindInMemory(
            UNALIGNED_INSTANCE_PATTERN_HEAP,
            range,
            8,
            error,
        )
        self.assertSuccess(error)
        self.assertEqual(addr, lldb.LLDB_INVALID_ADDRESS)

    def test_memory_info_list_iterable(self):
        """Make sure the SBMemoryRegionInfoList is iterable and each yielded object is unique"""
        self.assertTrue(self.process, PROCESS_IS_VALID)
        self.assertState(self.process.GetState(), lldb.eStateStopped, PROCESS_STOPPED)

        info_list = self.process.GetMemoryRegions()
        self.assertTrue(info_list.GetSize() > 0)

        collected_info = []
        try:
            for info in info_list:
                collected_info.append(info)
        except Exception:
            self.fail("SBMemoryRegionInfoList is not iterable")

        for i in range(len(collected_info)):
            region = lldb.SBMemoryRegionInfo()
            info_list.GetMemoryRegionAtIndex(i, region)

            self.assertEqual(
                collected_info[i],
                region,
                f"items {i}: iterator data should match index access data",
            )

        self.assertTrue(
            len(collected_info) >= 2, "Test requires at least 2 memory regions"
        )
        self.assertNotEqual(
            collected_info[0].GetRegionBase(),
            collected_info[1].GetRegionBase(),
            "Different items should have different base addresses",
        )
