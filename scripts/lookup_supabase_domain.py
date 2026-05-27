import dns.resolver

def main():
    domain = "db.dthmeuawwlsnzxkizxuf.supabase.co"
    print(f"Resolving DNS records for {domain}...")
    try:
        # Check CNAME
        answers = dns.resolver.resolve(domain, 'CNAME')
        for rdata in answers:
            print(f"CNAME: {rdata.target}")
    except Exception as e:
        print(f"CNAME failed: {e}")

    try:
        # Check AAAA (IPv6)
        answers = dns.resolver.resolve(domain, 'AAAA')
        for rdata in answers:
            print(f"AAAA: {rdata.address}")
    except Exception as e:
        print(f"AAAA failed: {e}")

if __name__ == "__main__":
    main()
