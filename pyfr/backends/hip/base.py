# -*- coding: utf-8 -*-

import re

from pyfr.backends.base import BaseBackend
from pyfr.mpiutil import get_local_rank


class HIPBackend(BaseBackend):
    name = 'hip'

    def __init__(self, cfg):
        super().__init__(cfg)

        from pyfr.backends.hip.wrappers import HIP

        # Create the HIP context
        self.hip = HIP()

        # Get the desired HIP device
        devid = cfg.get('backend-hip', 'device-id', 'local-rank')
        if not re.match(r'(local-rank|\d+)$', devid):
            raise ValueError('Invalid device-id')

        # Handle the local-rank case
        if devid == 'local-rank':
            devid = str(get_local_rank())

        # Set the device
        self.hip.set_device(int(devid))

        # Take the required alignment to be 128 bytes
        self.alignb = 128

        # Take the SoA size to be 32 elements
        self.soasz = 32

        from pyfr.backends.hip import (blasext, gimmik, packing, provider,
                                       rocblas, types)

        # Register our data types
        self.base_matrix_cls = types.HIPMatrixBase
        self.const_matrix_cls = types.HIPConstMatrix
        self.matrix_cls = types.HIPMatrix
        self.matrix_bank_cls = types.HIPMatrixBank
        self.matrix_slice_cls = types.HIPMatrixSlice
        self.queue_cls = types.HIPQueue
        self.view_cls = types.HIPView
        self.xchg_matrix_cls = types.HIPXchgMatrix
        self.xchg_view_cls = types.HIPXchgView

        # Instantiate the base kernel providers
        kprovs = [provider.HIPPointwiseKernelProvider,
                  blasext.HIPBlasExtKernels,
                  packing.HIPPackingKernels,
                  gimmik.HIPGiMMiKKernels,
                  rocblas.HIPRocBLASKernels]
        self._providers = [k(self) for k in kprovs]

        # Pointwise kernels
        self.pointwise = self._providers[0]

    def _malloc_impl(self, nbytes):
        # Allocate
        data = self.hip.mem_alloc(nbytes)

        # Zero
        self.hip.memset(data, 0, nbytes)

        return data