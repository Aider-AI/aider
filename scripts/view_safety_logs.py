"""
View safety audit logs
"""

from aider.safety import get_audit_logger

def main():
    logger = get_audit_logger()
    
    print("=" * 60)
    print("SAFETY AUDIT LOG")
    print("=" * 60)
    
    stats = logger.get_stats()
    print(f"\n📊 Statistics:")
    print(f"  Total Checks: {stats['total_checks']}")
    print(f"  Confirmations Required: {stats['confirmations_required']}")
    print(f"  User Approved: {stats['user_approved'] or 0}")
    print(f"  User Rejected: {stats['user_rejected'] or 0}")
    print(f"  Average Risk Score: {stats['avg_risk_score']:.2f}")
    print(f"  Max Risk Score: {stats['max_risk_score']:.2f}")
    
    print(f"\n📋 Recent Checks:")
    recent = logger.get_recent_checks(limit=10)
    
    for check in recent:
        print(f"\n  [{check['timestamp']}]")
        print(f"  File: {check['filename']}")
        print(f"  Safe: {'✅' if check['is_safe'] else '⚠️'}")
        print(f"  Risk Score: {check['risk_score']:.2f}")
        if check['user_approved'] is not None:
            approved = "✅ Approved" if check['user_approved'] else "❌ Rejected"
            print(f"  User Decision: {approved}")

if __name__ == '__main__':
    main()