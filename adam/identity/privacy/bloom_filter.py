# =============================================================================
# ADAM Enhancement #19: Bloom Filter Matching
# Location: adam/identity/privacy/bloom_filter.py
# =============================================================================

"""
Privacy-preserving identity matching using Bloom filters.

Enables secure matching in clean room environments:
- No raw identifiers exchanged
- Probabilistic matching with tunable FPR
- Suitable for partner integrations
"""

from typing import List, Set, Optional, Tuple
from pydantic import BaseModel, Field
import hashlib
import math
import logging

logger = logging.getLogger(__name__)


def _hash_pair(item: str) -> tuple:
    """Generate two hash values using SHA256 and MD5."""
    h1 = int(hashlib.sha256(item.encode()).hexdigest(), 16)
    h2 = int(hashlib.md5(item.encode()).hexdigest(), 16)
    return h1, h2


class BloomFilterConfig(BaseModel):
    """Configuration for Bloom filter."""
    
    expected_elements: int = Field(1000000, description="Expected number of elements")
    false_positive_rate: float = Field(0.01, description="Target FPR (1%)")
    
    @property
    def optimal_size(self) -> int:
        """Calculate optimal bit array size."""
        n = self.expected_elements
        p = self.false_positive_rate
        m = -1 * (n * math.log(p)) / (math.log(2) ** 2)
        return int(m)
    
    @property
    def optimal_hash_count(self) -> int:
        """Calculate optimal number of hash functions."""
        m = self.optimal_size
        n = self.expected_elements
        k = (m / n) * math.log(2)
        return int(k)


class BloomFilter:
    """
    Bloom filter for privacy-preserving set membership.
    
    Used for matching identifiers without revealing raw values.
    """
    
    def __init__(
        self,
        size: int = 10000000,
        hash_count: int = 7,
        config: Optional[BloomFilterConfig] = None
    ):
        if config:
            size = config.optimal_size
            hash_count = config.optimal_hash_count
        
        self.size = size
        self.hash_count = hash_count
        self.bit_array = bytearray((size + 7) // 8)
        self._element_count = 0
    
    def _get_hash_values(self, item: str) -> List[int]:
        """Generate hash values for an item."""
        # Use double hashing: h(i) = h1(x) + i*h2(x)
        h1, h2 = _hash_pair(item)
        h1 = h1 % self.size
        h2 = h2 % self.size
        
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]
    
    def add(self, item: str) -> None:
        """Add item to the filter."""
        for bit_index in self._get_hash_values(item):
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            self.bit_array[byte_index] |= (1 << bit_offset)
        self._element_count += 1
    
    def add_batch(self, items: List[str]) -> int:
        """Add multiple items to the filter."""
        for item in items:
            self.add(item)
        return len(items)
    
    def contains(self, item: str) -> bool:
        """Check if item might be in the filter."""
        for bit_index in self._get_hash_values(item):
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            if not (self.bit_array[byte_index] & (1 << bit_offset)):
                return False
        return True
    
    def check_batch(self, items: List[str]) -> List[bool]:
        """Check multiple items."""
        return [self.contains(item) for item in items]
    
    def intersection_estimate(self, other: "BloomFilter") -> float:
        """Estimate intersection size with another filter."""
        if self.size != other.size:
            raise ValueError("Filters must have same size")
        
        # Count bits set in both
        intersection_bits = 0
        for i in range(len(self.bit_array)):
            intersection_bits += bin(self.bit_array[i] & other.bit_array[i]).count('1')
        
        # Estimate intersection using formula
        m = self.size
        k = self.hash_count
        x = intersection_bits / m
        
        if x == 0:
            return 0.0
        
        # n ≈ -m/k * ln(1 - x)
        estimated = -m / k * math.log(1 - x)
        return max(0, estimated)
    
    @property
    def element_count(self) -> int:
        """Number of elements added."""
        return self._element_count
    
    @property
    def fill_ratio(self) -> float:
        """Ratio of bits set to total bits."""
        bits_set = sum(bin(b).count('1') for b in self.bit_array)
        return bits_set / self.size
    
    @property
    def estimated_false_positive_rate(self) -> float:
        """Estimated current false positive rate."""
        # (1 - e^(-kn/m))^k
        k = self.hash_count
        n = self._element_count
        m = self.size
        return (1 - math.exp(-k * n / m)) ** k
    
    def serialize(self) -> bytes:
        """Serialize filter for transmission."""
        return bytes(self.bit_array)
    
    @classmethod
    def deserialize(
        cls,
        data: bytes,
        hash_count: int = 7
    ) -> "BloomFilter":
        """Deserialize filter from bytes."""
        bf = cls(size=len(data) * 8, hash_count=hash_count)
        bf.bit_array = bytearray(data)
        return bf


class BloomFilterMatcher:
    """
    Privacy-preserving identifier matching using Bloom filters.
    
    Used for clean room matching where raw identifiers cannot
    be shared between parties.
    """
    
    def __init__(
        self,
        config: Optional[BloomFilterConfig] = None
    ):
        self.config = config or BloomFilterConfig()
        
        # Create filters for different identifier types
        self.filters = {}
    
    def create_filter(
        self,
        identifier_type: str,
        identifiers: List[str]
    ) -> BloomFilter:
        """Create and populate a filter for an identifier type."""
        bf = BloomFilter(config=self.config)
        bf.add_batch(identifiers)
        self.filters[identifier_type] = bf
        return bf
    
    def match(
        self,
        identifier_type: str,
        identifiers: List[str]
    ) -> List[Tuple[str, bool]]:
        """Check identifiers against stored filter."""
        if identifier_type not in self.filters:
            return [(id, False) for id in identifiers]
        
        bf = self.filters[identifier_type]
        return [(id, bf.contains(id)) for id in identifiers]
    
    def estimate_overlap(
        self,
        identifier_type: str,
        partner_filter: BloomFilter
    ) -> float:
        """Estimate overlap with partner's filter."""
        if identifier_type not in self.filters:
            return 0.0
        
        return self.filters[identifier_type].intersection_estimate(partner_filter)
    
    def export_filter(self, identifier_type: str) -> Optional[bytes]:
        """Export filter for sharing with partner."""
        if identifier_type not in self.filters:
            return None
        return self.filters[identifier_type].serialize()
    
    def import_filter(
        self,
        identifier_type: str,
        data: bytes,
        hash_count: int = 7
    ) -> BloomFilter:
        """Import filter from partner."""
        bf = BloomFilter.deserialize(data, hash_count)
        self.filters[f"partner_{identifier_type}"] = bf
        return bf
