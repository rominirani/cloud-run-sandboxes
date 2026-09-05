def two_sum(nums, target):
    """Optimal O(N) solution using a hash map."""
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
